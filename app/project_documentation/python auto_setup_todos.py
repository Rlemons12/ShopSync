# app/modules/database/loadsheets/loader/loader_equipment_relationships_db.py
from __future__ import annotations

import argparse
import sys
from typing import Optional, Dict, Any, Iterable

# --- Logging helpers (use your app's if available) ---
try:
    from app.modules.configuration import set_request_id, info_id, debug_id, error_id
except Exception:
    # Fallbacks if your logging helpers aren't importable in this context
    def set_request_id() -> str:
        return "loader"

    def info_id(msg: str, *args, **kwargs):
        print("[INFO]", msg % args if args else msg)

    def debug_id(msg: str, *args, **kwargs):
        print("[DEBUG]", msg % args if args else msg)

    def error_id(msg: str, *args, **kwargs):
        print("[ERROR]", msg % args if args else msg)

# --- Config & DB session ---
from app.modules.configuration.config import (
    EQUIPMENT_RELATIONSHIPS_XLSX,
    DATABASE_URL,  # exposed by config for convenience
)
from app.modules.configuration.database_config import DatabaseConfig

# Create one global instance for this loader
db_config = DatabaseConfig()

def get_main_session():
    """Return a new SQLAlchemy session bound to the configured database."""
    return db_config.get_main_session()


# --- SQLAlchemy & models ---
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# DB is source of truth
from app.modules.database.shopsync_db import (
    Campus,
    Building,
    SiteLocation,
    Position,
)

# --- Pandas for reading the Excel workbook ---
try:
    import pandas as pd
except ImportError as e:
    raise RuntimeError("pandas is required to run this loader. pip install pandas") from e


# ====================================================
# Header / Sheet normalization & legacy compatibility
# ====================================================

# Map DB-native and legacy headers -> canonical loader names
HEADER_MAP = {
    # Campus
    "name": "CampusName",
    "campusname": "CampusName",
    "campus_name": "CampusName",

    "description": "CampusDescription",
    "campusdescription": "CampusDescription",
    "campus_description": "CampusDescription",

    "city": "City",
    "state": "State",
    "country": "Country",

    # Building
    "buildingname": "BuildingName",
    "building_name": "BuildingName",
    "buildingdescription": "BuildingDescription",
    "building_description": "BuildingDescription",
    "address": "Address",

    # SiteLocation
    "title": "SiteLocationTitle",
    "sitelocationtitle": "SiteLocationTitle",
    "site_location_title": "SiteLocationTitle",
    "roomnumber": "RoomNumber",
    "room_number": "RoomNumber",
    "sitearea": "SiteArea",
    "site_area": "SiteArea",

    # Position FKs (typos/variants)
    "areaid": "AreaId",
    "are_id": "AreaId",
    "equipmentgroupid": "EquipmentGroupId",
    "modelid": "ModelId",
    "assetnumberid": "AssetNumberId",
    "locationid": "LocationId",
    "subassemblyid": "SubassemblyId",
    "componentassemblyid": "ComponentAssemblyId",
    "assemblyviewid": "AssemblyViewId",
}

# Accept common sheet name variations
SHEET_ALIASES = {
    "site": "SiteLocation",
    "site location": "SiteLocation",
    "campuses": "Campus",
    "buildings": "Building",
    "positions": "Position",
}

EXPECTED_SHEETS = {"Campus", "Building", "SiteLocation", "Position"}


def _normalize_header(name: str) -> str:
    s = str(name or "").strip()
    key = s.lower().replace(" ", "").replace("-", "").replace("\u00A0", "")
    return HEADER_MAP.get(key, s)


def _normalize_dataframe(df: "pd.DataFrame") -> "pd.DataFrame":
    # Normalize headers; trim strings; drop fully empty rows
    df = df.rename(columns=lambda c: _normalize_header(c))
    df = df.applymap(lambda v: v.strip() if isinstance(v, str) else v)
    df = df.dropna(how="all")
    return df


def _resolve_sheet_names(actual_sheet_names) -> list[str]:
    resolved = []
    lowered = {s.lower(): s for s in actual_sheet_names}
    for wanted in EXPECTED_SHEETS:
        if wanted in actual_sheet_names:
            resolved.append(wanted)
            continue
        # try alias
        for alias, canonical in SHEET_ALIASES.items():
            if canonical == wanted and alias in lowered:
                resolved.append(lowered[alias])
                break
    return resolved


# =================
# Utility / Caches
# =================
def key_lower(*parts: Any) -> str:
    """Normalized cache key helper."""
    return "|".join("" if p is None else str(p).strip().lower() for p in parts)


class Cache:
    """Simple in-memory caches to minimize DB lookups during a single run."""
    def __init__(self):
        self.campus: Dict[str, int] = {}
        self.building: Dict[str, int] = {}
        self.site_location: Dict[str, int] = {}


# ===============================
# Get-or-create helpers (schema)
# ===============================
def get_or_create_campus(session, cache: Cache, name: str, **extra) -> int:
    k = key_lower(name)
    if k in cache.campus:
        return cache.campus[k]

    obj = session.query(Campus).filter(Campus.name.ilike(name)).one_or_none()
    if obj is None:
        obj = Campus(
            name=name,
            description=extra.get("description"),
            city=extra.get("city"),
            state=extra.get("state"),
            country=extra.get("country"),
        )
        session.add(obj)
        session.flush()
        info_id(f"Created Campus '{name}' (id={obj.id})")
    cache.campus[k] = obj.id
    return obj.id


def get_or_create_building(session, cache: Cache, name: str, campus_name: str, **extra) -> int:
    # Resolve campus id
    ck = key_lower(campus_name)
    campus_id = cache.campus.get(ck)
    if campus_id is None:
        camp = session.query(Campus).filter(Campus.name.ilike(campus_name)).one_or_none()
        if not camp:
            campus_id = get_or_create_campus(session, cache, campus_name)
        else:
            campus_id = camp.id
            cache.campus[ck] = campus_id

    k = key_lower(name, campus_name)
    if k in cache.building:
        return cache.building[k]

    obj = (
        session.query(Building)
        .filter(Building.name.ilike(name), Building.campus_id == campus_id)
        .one_or_none()
    )
    if obj is None:
        obj = Building(
            name=name,
            description=extra.get("description"),
            address=extra.get("address"),
            campus_id=campus_id,
        )
        session.add(obj)
        session.flush()
        info_id(f"Created Building '{name}' in Campus '{campus_name}' (id={obj.id})")
    cache.building[k] = obj.id
    return obj.id


def get_or_create_site_location(
    session,
    cache: Cache,
    title: str,
    building_name: str,
    room_number: Optional[str] = None,
    site_area: Optional[str] = None,
) -> int:
    # Resolve building id
    bkey = key_lower(building_name)
    building_id = cache.building.get(bkey)
    if building_id is None:
        bobj = session.query(Building).filter(Building.name.ilike(building_name)).one_or_none()
        if not bobj:
            raise ValueError(f"Unknown Building '{building_name}' for SiteLocation '{title}'")
        building_id = bobj.id
        cache.building[bkey] = building_id

    # Title/room/site_area are non-null in current schema → default to "UNKNOWN" if blank
    room_number = (room_number or "").strip() or "UNKNOWN"
    site_area   = (site_area or "").strip() or "UNKNOWN"

    k = key_lower(title, building_name, room_number, site_area)
    if k in cache.site_location:
        return cache.site_location[k]

    obj = (
        session.query(SiteLocation)
        .filter(
            SiteLocation.title.ilike(title),
            SiteLocation.building_id == building_id,
            SiteLocation.room_number == room_number,
            SiteLocation.site_area == site_area,
        )
        .one_or_none()
    )
    if obj is None:
        obj = SiteLocation(
            title=title,
            room_number=room_number,
            site_area=site_area,
            building_id=building_id,
        )
        session.add(obj)
        session.flush()
        info_id(
            f"Created SiteLocation '{title}' (room={room_number}, area={site_area}) "
            f"in Building '{building_name}' (id={obj.id})"
        )

    cache.site_location[k] = obj.id
    return obj.id


def get_or_create_position(session, ids: Dict[str, Optional[int]]) -> int:
    """
    Create or reuse a Position row for the exact set of FK fields provided.
    Only current, schema-valid keys are considered.
    """
    valid_keys = [
        "area_id", "equipment_group_id", "model_id", "asset_number_id", "location_id",
        "subassembly_id", "component_assembly_id", "assembly_view_id",
        "site_location_id", "building_id", "campus_id"
    ]
    filters = {k: ids.get(k) for k in valid_keys if k in ids}

    obj = session.query(Position).filter_by(**filters).one_or_none()
    if obj is None:
        obj = Position(**filters)
        session.add(obj)
        session.flush()
        info_id(
            "Created Position id=%s with FKs: %s",
            obj.id,
            ", ".join(f"{k}={v}" for k, v in filters.items() if v is not None),
        )
    else:
        debug_id("Reused Position id=%s", obj.id)
    return obj.id


# =================
# Sheet loaders
# =================
def load_campus_sheet(session, df: "pd.DataFrame", cache: Cache, stop_on_error: bool):
    for i, row in df.iterrows():
        try:
            campus_name = (row.get("CampusName") or "").strip()
            if not campus_name:
                debug_id("Row %s skipped: empty CampusName", i)
                continue

            extra = dict(
                description=(row.get("CampusDescription") or None),
                city=(row.get("City") or None),
                state=(row.get("State") or None),
                country=(row.get("Country") or None),
            )
            get_or_create_campus(session, cache, campus_name, **extra)
        except Exception as e:
            error_id("Campus row %s failed: %s", i, e)
            if stop_on_error:
                raise


def load_building_sheet(session, df: "pd.DataFrame", cache: Cache, stop_on_error: bool):
    for i, row in df.iterrows():
        try:
            campus_name = str(row.get("CampusName") or "").strip()
            building_name = str(row.get("BuildingName") or "").strip()
            if not campus_name or not building_name:
                debug_id("Row %s skipped: missing CampusName or BuildingName", i)
                continue
            extra = dict(
                description=(row.get("BuildingDescription") or None),
                address=(row.get("Address") or None),
            )
            # Ensure campus first
            get_or_create_campus(session, cache, campus_name)
            get_or_create_building(session, cache, building_name, campus_name, **extra)
        except Exception as e:
            error_id("Building row %s failed: %s", i, e)
            if stop_on_error:
                raise


def load_site_location_sheet(session, df: "pd.DataFrame", cache: Cache, stop_on_error: bool):
    for i, row in df.iterrows():
        try:
            building_name = str(row.get("BuildingName") or "").strip()
            title = str(row.get("SiteLocationTitle") or "").strip()
            room_number = str(row.get("RoomNumber") or "").strip() if row.get("RoomNumber") is not None else None
            site_area = str(row.get("SiteArea") or "").strip() if row.get("SiteArea") is not None else None
            if not building_name or not title:
                debug_id("Row %s skipped: missing BuildingName or SiteLocationTitle", i)
                continue
            get_or_create_site_location(session, cache, title, building_name, room_number, site_area)
        except Exception as e:
            error_id("SiteLocation row %s failed: %s", i, e)
            if stop_on_error:
                raise


def load_position_sheet(session, df: "pd.DataFrame", cache: Cache, stop_on_error: bool):
    """
    Expected columns (case-insensitive, DB-native accepted via normalization):
      CampusName (optional), BuildingName (optional), SiteLocationTitle (optional),
      RoomNumber (optional), SiteArea (optional)
      Plus any FK columns you support:
        AreaId, EquipmentGroupId, ModelId, AssetNumberId, LocationId,
        SubassemblyId, ComponentAssemblyId, AssemblyViewId
    """
    for i, row in df.iterrows():
        try:
            ids: Dict[str, Optional[int]] = {}

            # Resolve optional high-level links
            campus_name = str(row.get("CampusName") or "").strip()
            if campus_name:
                camp = session.query(Campus).filter(Campus.name.ilike(campus_name)).one_or_none()
                if camp:
                    ids["campus_id"] = camp.id
                else:
                    ids["campus_id"] = get_or_create_campus(session, cache, campus_name)

            building_name = str(row.get("BuildingName") or "").strip()
            if building_name:
                b = session.query(Building).filter(Building.name.ilike(building_name)).one_or_none()
                if not b and campus_name:
                    b_id = get_or_create_building(session, cache, building_name, campus_name)
                    ids["building_id"] = b_id
                elif b:
                    ids["building_id"] = b.id

            # Resolve SiteLocation if provided
            site_title = str(row.get("SiteLocationTitle") or "").strip()
            room_num = str(row.get("RoomNumber") or "").strip() if row.get("RoomNumber") is not None else None
            site_area = str(row.get("SiteArea") or "").strip() if row.get("SiteArea") is not None else None
            if site_title and building_name:
                sl_id = get_or_create_site_location(session, cache, site_title, building_name, room_num, site_area)
                ids["site_location_id"] = sl_id

            # Lower-level FK columns (optional)
            def _int_or_none(val) -> Optional[int]:
                try:
                    if val is None or (isinstance(val, float) and pd.isna(val)):
                        return None
                    s = str(val).strip()
                    if not s:
                        return None
                    return int(float(s))  # safe for "1.0" typed sheets
                except Exception:
                    return None

            ids["area_id"] = _int_or_none(row.get("AreaId"))
            ids["equipment_group_id"] = _int_or_none(row.get("EquipmentGroupId"))
            ids["model_id"] = _int_or_none(row.get("ModelId"))
            ids["asset_number_id"] = _int_or_none(row.get("AssetNumberId"))
            ids["location_id"] = _int_or_none(row.get("LocationId"))
            ids["subassembly_id"] = _int_or_none(row.get("SubassemblyId"))
            ids["component_assembly_id"] = _int_or_none(row.get("ComponentAssemblyId"))
            ids["assembly_view_id"] = _int_or_none(row.get("AssemblyViewId"))

            # Create or reuse the Position for this exact FK set
            get_or_create_position(session, ids)

        except Exception as e:
            error_id("Position row %s failed: %s", i, e)
            if stop_on_error:
                raise


# =================
# Orchestrator
# =================
SHEET_LOADERS = {
    "Campus": load_campus_sheet,
    "Building": load_building_sheet,
    "SiteLocation": load_site_location_sheet,
    "Position": load_position_sheet,
}


def load_workbook(session, xlsx_path: str, only: Optional[Iterable[str]] = None, stop_on_error: bool = False):
    request_id = set_request_id()
    info_id(f"[{request_id}] Loading workbook: {xlsx_path}")

    xl = pd.ExcelFile(xlsx_path)

    # Compute the list of sheets to process (support aliases)
    if only:
        desired = []
        for s in only:
            if s in xl.sheet_names:
                desired.append(s)
                continue
            s_low = s.lower()
            for actual in xl.sheet_names:
                if actual.lower() == s_low:
                    desired.append(actual)
                    break
        to_process = desired
    else:
        to_process = _resolve_sheet_names(xl.sheet_names)

    info_id(f"Sheets to process: {to_process}")

    cache = Cache()

    # ---- Build auxiliary id->name maps for legacy FKs ----
    campus_id_to_name: Dict[Any, str] = {}
    building_id_to_name: Dict[Any, str] = {}

    if "Campus" in xl.sheet_names:
        cdf_raw = xl.parse("Campus")
        cdf = _normalize_dataframe(cdf_raw)
        if "id" in cdf.columns and "CampusName" in cdf.columns:
            campus_id_to_name = dict(zip(cdf["id"], cdf["CampusName"]))

    if "Building" in xl.sheet_names:
        bdf_raw = xl.parse("Building")
        bdf = _normalize_dataframe(bdf_raw)
        # 'id' sometimes appears as 'id ' with trailing space in legacy files
        bid_col = "id" if "id" in bdf.columns else ("id " if "id " in bdf.columns else None)
        if bid_col and "BuildingName" in bdf.columns:
            building_id_to_name = dict(zip(bdf[bid_col], bdf["BuildingName"]))

    # ---- Process sheets ----
    for sheet_name in to_process:
        if sheet_name not in xl.sheet_names:
            debug_id(f"Sheet '{sheet_name}' not present in workbook; skipping.")
            continue

        raw_df = xl.parse(sheet_name)
        df = _normalize_dataframe(raw_df)
        debug_id(f"[{sheet_name}] Columns detected: {list(df.columns)}")

        # Enrich Building sheet: derive CampusName from legacy id_building_complex if needed
        if sheet_name == "Building":
            # tolerate minor variants (e.g., stray spaces)
            legacy_col = None
            for c in df.columns:
                if c.strip().lower() == "id_building_complex":
                    legacy_col = c
                    break
            if legacy_col and "CampusName" not in df.columns and campus_id_to_name:
                df["CampusName"] = df[legacy_col].map(campus_id_to_name).fillna(None)

        # Enrich SiteLocation sheet: derive BuildingName from legacy building_id if needed
        if sheet_name in ("SiteLocation", "site"):
            if "BuildingName" not in df.columns and "building_id" in df.columns and building_id_to_name:
                df["BuildingName"] = df["building_id"].map(building_id_to_name).fillna(None)

        # Map alias sheet names to canonical key for the loader registry
        canonical = sheet_name
        if sheet_name not in SHEET_LOADERS and sheet_name.lower() in SHEET_ALIASES:
            canonical = SHEET_ALIASES[sheet_name.lower()]

        loader = SHEET_LOADERS.get(canonical)
        if not loader:
            debug_id(f"No loader registered for sheet '{sheet_name}' (canonical '{canonical}'); skipping.")
            continue

        info_id(f"Processing sheet '{sheet_name}' with {len(df)} rows...")
        loader(session, df, cache, stop_on_error)

    info_id(f"[{request_id}] Workbook load complete.")


# =========
# CLI
# =========
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ShopSync equipment relationships loader")
    p.add_argument(
        "--file", "-f",
        default=EQUIPMENT_RELATIONSHIPS_XLSX,
        help=f"Path to Excel workbook (default: {EQUIPMENT_RELATIONSHIPS_XLSX})"
    )
    p.add_argument(
        "--db",
        default=None,
        help="Optional database URL; if omitted, uses app.modules.configuration.database_config.get_main_session()"
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and validate but do not commit changes"
    )
    p.add_argument(
        "--only",
        nargs="+",
        default=None,
        help=f"Only load specific sheets (choices: {list(SHEET_LOADERS.keys())} or their aliases)"
    )
    p.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately on first row error"
    )
    return p


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    # Session selection: either explicit --db or default session
    if args.db:
        info_id(f"Using DB URL from --db: {args.db}")
        engine = create_engine(args.db, future=True)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
    else:
        info_id("Using default DB session from database_config")
        session = get_main_session()

    try:
        load_workbook(session, args.file, only=args.only, stop_on_error=args.stop_on_error)

        if args.dry_run:
            info_id("Dry-run enabled: rolling back all changes.")
            session.rollback()
        else:
            session.commit()
            info_id("Committed changes to the database.")
        return 0

    except SQLAlchemyError as db_err:
        session.rollback()
        error_id(f"Database error: {db_err}")
        if args.stop_on_error:
            return 1

    except Exception as e:
        session.rollback()
        error_id(f"Fatal error: {e}")
        if args.stop_on_error:
            return 1

    finally:
        try:
            session.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
