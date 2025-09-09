from __future__ import annotations
import argparse
import sys
from typing import Optional, Dict, Any, Iterable
import pandas as pd
from app.modules.database.shopsync_db import SiteLocation

# --- Logging helpers ---
try:
    from app.modules.configuration import set_request_id, info_id, debug_id, error_id
except Exception:
    def set_request_id() -> str:
        return "loader"

    def info_id(msg: str, *args, **kwargs):
        print("[INFO]", msg)

    def debug_id(msg: str, *args, **kwargs):
        print("[DEBUG]", msg)

    def error_id(msg: str, *args, **kwargs):
        print("[ERROR]", msg)

# --- Config & DB session ---
from app.modules.configuration.config import EQUIPMENT_RELATIONSHIPS_XLSX
from app.modules.configuration.database_config import DatabaseConfig

db_config = DatabaseConfig()

def get_main_session():
    return db_config.get_main_session()

# --- SQLAlchemy Models & utilities ---
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# Import models (adjust path if your project structure differs)
from app.modules.database.shopsync_db import (
    Campus, Building, SiteLocation, Position, Area, EquipmentGroup,
    Model, AssetNumber, Location, Subassembly, ComponentAssembly, AssemblyView,
)

try:
    import pandas as pd
except ImportError as e:
    raise RuntimeError("pandas is required to run this loader. pip install pandas") from e


# --- Database Validation Functions ---
def validate_database_connection(session) -> bool:
    try:
        session.execute(text("SELECT 1"))
        info_id("Database connection successful")
        return True
    except Exception as e:
        error_id(f"Database connection failed: {e}")
        return False


def check_required_tables(session) -> Dict[str, bool]:
    required_tables = {
        'campus': Campus,
        'building': Building,
        'site_location': SiteLocation,
        'area': Area,
        'equipment_group': EquipmentGroup,
        'model': Model,
        'asset_number': AssetNumber,
        'location': Location,
        'position': Position,
        'subassembly': Subassembly,
        'component_assembly': ComponentAssembly,
        'assembly_view': AssemblyView,
    }

    inspector = inspect(session.bind)
    existing_tables = inspector.get_table_names()

    table_status = {}
    for table_name in required_tables:
        exists = table_name in existing_tables
        table_status[table_name] = exists
        if exists:
            info_id(f"OK Table '{table_name}' exists")
        else:
            error_id(f"ERROR Table '{table_name}' missing")

    return table_status


def create_missing_tables(session) -> bool:
    try:
        info_id("Creating missing database tables...")
        db_config.create_all()
        info_id("Database tables created successfully")
        return True
    except Exception as e:
        error_id(f"Failed to create tables: {e}")
        return False


def validate_table_schema(session) -> bool:
    try:
        inspector = inspect(session.bind)

        # Defensive: detect bad 'are_id' vs 'area_id'
        position_columns = [col['name'] for col in inspector.get_columns('position')]
        if 'are_id' in position_columns:
            error_id("SCHEMA ERROR: Position table has 'are_id' instead of 'area_id'")
            return False
        if 'area_id' not in position_columns:
            error_id("SCHEMA ERROR: Position table missing 'area_id' column")
            return False

        info_id("[OK] Table schemas validated")
        return True

    except Exception as e:
        error_id(f"Schema validation failed: {e}")
        return False


def prepare_database(session, auto_create: bool = False) -> bool:
    request_id = set_request_id()
    info_id(f"[{request_id}] Starting database validation...")

    if not validate_database_connection(session):
        return False

    table_status = check_required_tables(session)
    missing_tables = [name for name, exists in table_status.items() if not exists]

    if missing_tables:
        error_id(f"Missing tables: {missing_tables}")
        if auto_create:
            if not create_missing_tables(session):
                return False
            table_status = check_required_tables(session)
            missing_tables = [name for name, exists in table_status.items() if not exists]
        if missing_tables:
            error_id("Cannot proceed with missing tables. Use --create-tables to auto-create them.")
            return False

    if not validate_table_schema(session):
        return False

    info_id(f"[{request_id}] Database validation completed successfully")
    return True


def check_database_only(session) -> bool:
    request_id = set_request_id()
    info_id(f"[{request_id}] Running database check only...")

    if not validate_database_connection(session):
        return False

    table_status = check_required_tables(session)
    missing_tables = [name for name, exists in table_status.items() if not exists]
    if missing_tables:
        error_id(f"Missing tables: {missing_tables}")
        error_id("Use --create-tables to auto-create missing tables.")
        return False

    if not validate_table_schema(session):
        return False

    info_id(f"[{request_id}] Database check completed successfully - all tables present and valid")
    return True


# --- Data Processing Utilities ---
def normalize_headers(df: "pd.DataFrame") -> "pd.DataFrame":
    """Trim header whitespace only; do not downcase to preserve explicit names."""
    return df.rename(columns={c: c.strip() for c in df.columns})


def get_int_or_none(v) -> Optional[int]:
    if v is None:
        return None
    try:
        s = str(v).strip()
        if s == "" or s.lower() == "none" or s.lower() == "nan":
            return None
        return int(float(s))  # handles numeric excel cells
    except Exception:
        return None


class Cache:
    """Simple in-memory caches to minimize DB lookups."""
    def __init__(self):
        self.campus: Dict[str, int] = {}
        self.building: Dict[str, int] = {}
        self.site_location: Dict[str, int] = {}
        self.area: Dict[str, int] = {}
        self.equipment_group: Dict[str, int] = {}
        self.model: Dict[str, int] = {}
        self.asset_number: Dict[str, int] = {}
        self.location: Dict[str, int] = {}

def key_lower(*parts: Any) -> str:
    return "|".join("" if p is None else str(p).strip().lower() for p in parts)


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

import pandas as pd
from app.modules.database.shopsync_db import SiteLocation

def _s(value) -> str:
    """Convert any cell value to a clean string, or '' if empty/NaN."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()

def get_or_create_site_location(session, *, title, room_number=None, site_area=None, request_id=None, logger=None):
    # Coerce inputs to safe strings
    title = _s(title)
    room_number = _s(room_number)
    site_area = _s(site_area)

    # Lookup
    q = session.query(SiteLocation).filter(
        SiteLocation.title == title,
        SiteLocation.room_number == room_number
    )
    obj = q.first()
    if obj:
        if logger:
            logger.info(f"[{request_id}] Found SiteLocation '{obj.title}' (id={obj.id}) room={obj.room_number}")
        return obj, False

    # Create new SiteLocation
    obj = SiteLocation(
        title=title,
        room_number=room_number,
        site_area=site_area
    )
    session.add(obj)
    session.flush()  # get an id

    if logger:
        logger.info(
            f"[{request_id}] Created SiteLocation '{obj.title}' (id={obj.id}) "
            f"room={obj.room_number} site_area={obj.site_area}"
        )
    return obj, True


def get_or_create_area(session, cache: Cache, name: str, description: Optional[str] = None) -> int:
    k = key_lower(name)
    if k in cache.area:
        return cache.area[k]
    obj = session.query(Area).filter(Area.name.ilike(name)).one_or_none()
    if obj is None:
        obj = Area(name=name, description=description)
        session.add(obj)
        session.flush()
        info_id(f"Created Area '{name}' (id={obj.id})")
    cache.area[k] = obj.id
    return obj.id


def get_or_create_building(session, cache: Cache, name: str, campus_ref: Optional[str | int], **extra) -> int:
    """
    campus_ref can be campus_id (int) or campus_name (str).
    We de-dupe by (name, campus_id).
    """
    # resolve campus_id
    campus_id: Optional[int] = None
    if isinstance(campus_ref, int):
        campus_id = campus_ref
    else:
        campus_name = (campus_ref or "").strip()
        if campus_name:
            campus_id = get_or_create_campus(session, cache, campus_name)
    if campus_id is None:
        # last resort: first campus or create DEFAULT
        default_name = "DEFAULT"
        campus_id = get_or_create_campus(session, cache, default_name)

    k = key_lower(name, campus_id)
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
        info_id(f"Created Building '{name}' (id={obj.id}) campus_id={campus_id}")
    cache.building[k] = obj.id
    return obj.id


def get_or_create_equipment_group(session, cache: Cache, name: str,
                                  area_ref: Optional[str | int], description: Optional[str] = None) -> int:
    """
    area_ref can be area_id (int) or area_name (str).
    De-dupe by (name, area_id).
    """
    area_id: Optional[int] = None
    if isinstance(area_ref, int):
        area_id = area_ref
    else:
        area_name = (area_ref or "").strip() or "GENERAL"
        area_id = get_or_create_area(session, cache, area_name)

    k = key_lower(name, area_id)
    if k in cache.equipment_group:
        return cache.equipment_group[k]

    obj = (
        session.query(EquipmentGroup)
        .filter(EquipmentGroup.name.ilike(name), EquipmentGroup.area_id == area_id)
        .one_or_none()
    )
    if obj is None:
        obj = EquipmentGroup(name=name, area_id=area_id, description=description)
        session.add(obj)
        session.flush()
        info_id(f"Created EquipmentGroup '{name}' (id={obj.id}) area_id={area_id}")
    cache.equipment_group[k] = obj.id
    return obj.id


def get_or_create_model(session, cache: Cache, name: str,
                        eg_ref: Optional[str | int], description: Optional[str] = None) -> int:
    """
    eg_ref can be equipment_group_id (int) or equipment_group_name (str).
    De-dupe by (name, equipment_group_id).
    """
    equipment_group_id: Optional[int] = None
    if isinstance(eg_ref, int):
        equipment_group_id = eg_ref
    else:
        eg_name = (eg_ref or "").strip() or "UNGROUPED"
        equipment_group_id = get_or_create_equipment_group(session, cache, eg_name, area_ref="GENERAL")

    k = key_lower(name, equipment_group_id)
    if k in cache.model:
        return cache.model[k]

    obj = (
        session.query(Model)
        .filter(Model.name.ilike(name), Model.equipment_group_id == equipment_group_id)
        .one_or_none()
    )
    if obj is None:
        obj = Model(name=name, description=description, equipment_group_id=equipment_group_id)
        session.add(obj)
        session.flush()
        info_id(f"Created Model '{name}' (id={obj.id}) equipment_group_id={equipment_group_id}")
    cache.model[k] = obj.id
    return obj.id


def get_or_create_asset_number(session, cache: Cache, number: str,
                               model_ref: Optional[str | int], description: Optional[str] = None) -> int:
    """
    model_ref can be model_id (int) or model_name (str).
    De-dupe by (number, model_id).
    """
    model_id: Optional[int] = None
    if isinstance(model_ref, int):
        model_id = model_ref
    else:
        model_name = (model_ref or "").strip() or "UNKNOWN_MODEL"
        model_id = get_or_create_model(session, cache, model_name, eg_ref="UNGROUPED")

    k = key_lower(number, model_id)
    if k in cache.asset_number:
        return cache.asset_number[k]

    obj = (
        session.query(AssetNumber)
        .filter(AssetNumber.number.ilike(number), AssetNumber.model_id == model_id)
        .one_or_none()
    )
    if obj is None:
        obj = AssetNumber(number=number, description=description, model_id=model_id)
        session.add(obj)
        session.flush()
        info_id(f"Created AssetNumber '{number}' (id={obj.id}) model_id={model_id}")
    cache.asset_number[k] = obj.id
    return obj.id


def get_or_create_location(session, cache: Cache, name: str,
                           model_ref: Optional[str | int], description: Optional[str] = None) -> int:
    """
    model_ref can be model_id (int) or model_name (str).
    De-dupe by (name, model_id).
    """
    model_id: Optional[int] = None
    if isinstance(model_ref, int):
        model_id = model_ref
    else:
        model_name = (model_ref or "").strip() or "UNKNOWN_MODEL"
        model_id = get_or_create_model(session, cache, model_name, eg_ref="UNGROUPED")

    k = key_lower(name, model_id)
    if k in cache.location:
        return cache.location[k]

    obj = (
        session.query(Location)
        .filter(Location.name.ilike(name), Location.model_id == model_id)
        .one_or_none()
    )
    if obj is None:
        obj = Location(name=name, description=description, model_id=model_id)
        session.add(obj)
        session.flush()
        info_id(f"Created Location '{name}' (id={obj.id}) model_id={model_id}")
    cache.location[k] = obj.id
    return obj.id


# --- Sheet Loaders ---
def load_campus_sheet(session, df, cache, stop_on_error):
    df = normalize_headers(df)
    for i, row in df.iterrows():
        try:
            campus_name = str(row.get("name") or "").strip()
            if not campus_name:
                debug_id(f"Campus row {i} skipped: empty name")
                continue
            extra = dict(
                description=(str(row.get("description") or "").strip() or None),
                city=(str(row.get("city") or "").strip() or None),
                state=(str(row.get("state") or "").strip() or None),
                country=(str(row.get("country") or "").strip() or None),
            )
            get_or_create_campus(session, cache, campus_name, **extra)
        except Exception as e:
            error_id(f"Campus row {i} failed: {e}")
            if stop_on_error:
                raise


def load_building_sheet(session, df, cache, stop_on_error):
    """
    Accepts either:
      - id, name, description, address, campus_id
      - name, description, address, campus_name
    """
    df = normalize_headers(df)
    for i, row in df.iterrows():
        try:
            name = str(row.get("name") or "").strip()
            if not name:
                debug_id(f"Building row {i} skipped: empty name")
                continue

            # prefer campus_id if present; fall back to campus_name
            campus_id = get_int_or_none(row.get("campus_id"))
            campus_ref = campus_id if campus_id is not None else (row.get("campus_name") or None)

            extra = dict(
                description=(str(row.get("description") or "").strip() or None),
                address=(str(row.get("address") or "").strip() or None),
            )
            get_or_create_building(session, cache, name, campus_ref, **extra)
        except Exception as e:
            error_id(f"Building row {i} failed: {e}")
            if stop_on_error:
                raise

def load_site_location(session, df, request_id=None, logger=None):
    # normalize columns
    df = df.rename(columns={c: c.strip() for c in df.columns})
    # accepted headers (extra columns will be ignored)
    # Expected columns in the worksheet: title, room_number, site_area
    required = ["title"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"SiteLocation sheet missing required columns: {missing}")

    for idx, row in df.iterrows():
        try:
            title = row.get("title")
            room_number = row.get("room_number")
            site_area = row.get("site_area")
            get_or_create_site_location(
                session,
                title=title,
                room_number=room_number,
                site_area=site_area,
                request_id=request_id,
                logger=logger,
            )
        except Exception as e:
            if logger:
                logger.error(f"[{request_id}] SiteLocation row {idx} failed: {e}")
            else:
                raise


def load_area_sheet(session, df, cache, stop_on_error):
    df = normalize_headers(df)
    for i, row in df.iterrows():
        try:
            area_name = str(row.get("name") or "").strip()
            if not area_name:
                debug_id(f"Area row {i} skipped: empty name")
                continue
            description = str(row.get("description") or "").strip() or None
            get_or_create_area(session, cache, area_name, description)
        except Exception as e:
            error_id(f"Area row {i} failed: {e}")
            if stop_on_error:
                raise


def load_equipment_group_sheet(session, df, cache, stop_on_error):
    """
    Accepts either:
      - id, name, area_id
      - name, area_name
      - name, area_id, description (optional)
    """
    df = normalize_headers(df)
    for i, row in df.iterrows():
        try:
            name = str(row.get("name") or "").strip()
            if not name:
                debug_id(f"EquipmentGroup row {i} skipped: empty name")
                continue

            desc = str(row.get("description") or "").strip() or None
            area_id = get_int_or_none(row.get("area_id"))
            area_ref = area_id if area_id is not None else (row.get("area_name") or "GENERAL")

            get_or_create_equipment_group(session, cache, name, area_ref, desc)
        except Exception as e:
            error_id(f"EquipmentGroup row {i} failed: {e}")
            if stop_on_error:
                raise


def load_model_sheet(session, df, cache, stop_on_error):
    """
    Accepts either:
      - id, name, description, equipment_group_id
      - name, description, equipment_group_name
    """
    df = normalize_headers(df)
    for i, row in df.iterrows():
        try:
            name = str(row.get("name") or "").strip()
            if not name:
                debug_id(f"Model row {i} skipped: empty name")
                continue
            desc = str(row.get("description") or "").strip() or None
            eg_id = get_int_or_none(row.get("equipment_group_id"))
            eg_ref = eg_id if eg_id is not None else (row.get("equipment_group_name") or "UNGROUPED")
            get_or_create_model(session, cache, name, eg_ref, description=desc)
        except Exception as e:
            error_id(f"Model row {i} failed: {e}")
            if stop_on_error:
                raise


def load_asset_number_sheet(session, df, cache, stop_on_error):
    """
    Accepts either:
      - id, number, description, model_id
      - number, description, model_name
    """
    df = normalize_headers(df)
    for i, row in df.iterrows():
        try:
            number = str(row.get("number") or "").strip()
            if not number:
                debug_id(f"AssetNumber row {i} skipped: empty number")
                continue
            desc = str(row.get("description") or "").strip() or None
            model_id = get_int_or_none(row.get("model_id"))
            model_ref = model_id if model_id is not None else (row.get("model_name") or "UNKNOWN_MODEL")
            get_or_create_asset_number(session, cache, number, model_ref, description=desc)
        except Exception as e:
            error_id(f"AssetNumber row {i} failed: {e}")
            if stop_on_error:
                raise


def load_location_sheet(session, df, cache, stop_on_error):
    """
    Accepts either:
      - id, name, description, model_id
      - name, description, model_name
    """
    df = normalize_headers(df)
    for i, row in df.iterrows():
        try:
            name = str(row.get("name") or "").strip()
            if not name:
                debug_id(f"Location row {i} skipped: empty name")
                continue
            desc = str(row.get("description") or "").strip() or None
            model_id = get_int_or_none(row.get("model_id"))
            model_ref = model_id if model_id is not None else (row.get("model_name") or "UNKNOWN_MODEL")
            get_or_create_location(session, cache, name, model_ref, description=desc)
        except Exception as e:
            error_id(f"Location row {i} failed: {e}")
            if stop_on_error:
                raise


def load_position_sheet(session, df, cache, stop_on_error):
    """
    Build a Position row from whatever FKs are provided.
    Columns accepted (any subset): area_id/area_name, equipment_group_id/equipment_group_name,
      model_id/model_name, asset_number/asset_number_id, location_id/location_name
    """
    df = normalize_headers(df)
    for i, row in df.iterrows():
        try:
            area_id = get_int_or_none(row.get("area_id"))
            eg_id = get_int_or_none(row.get("equipment_group_id"))
            model_id = get_int_or_none(row.get("model_id"))
            asset_id = get_int_or_none(row.get("asset_number_id"))
            location_id = get_int_or_none(row.get("location_id"))

            # allow name fallbacks
            if area_id is None:
                area_name = str(row.get("area_name") or "").strip()
                if area_name:
                    area_id = get_or_create_area(session, cache, area_name)
            if eg_id is None:
                eg_name = str(row.get("equipment_group_name") or "").strip()
                if eg_name:
                    eg_area = str(row.get("area_name") or "GENERAL").strip()
                    eg_id = get_or_create_equipment_group(session, cache, eg_name, eg_area)
            if model_id is None:
                model_name = str(row.get("model_name") or "").strip()
                if model_name:
                    model_id = get_or_create_model(session, cache, model_name, eg_id if eg_id else "UNGROUPED")
            if asset_id is None:
                asset_number = str(row.get("asset_number") or "").strip()
                if asset_number:
                    asset_id = get_or_create_asset_number(session, cache, asset_number, model_id if model_id else "UNKNOWN_MODEL")
            if location_id is None:
                location_name = str(row.get("location_name") or "").strip()
                if location_name:
                    location_id = get_or_create_location(session, cache, location_name, model_id if model_id else "UNKNOWN_MODEL")

            # Create/get Position using your model classmethod (must exist in shopsync_db.py)
            pos_id = Position.add_to_db(
                session=session,
                area_id=area_id,
                equipment_group_id=eg_id,
                model_id=model_id,
                asset_number_id=asset_id,
                location_id=location_id,
            )
            info_id(f"Upserted Position id={pos_id} (row {i})")
        except Exception as e:
            error_id(f"Position row {i} failed: {e}")
            if stop_on_error:
                raise


SHEET_LOADERS = {
    "Campus": load_campus_sheet,
    "Building": load_building_sheet,
    "Site": load_site_location,
    "Area": load_area_sheet,
    "EquipmentGroup": load_equipment_group_sheet,
    "Model": load_model_sheet,
    "AssetNumber": load_asset_number_sheet,
    "Location": load_location_sheet,
    "Position": load_position_sheet,

}


def load_workbook(session, xlsx_path: str, only: Optional[Iterable[str]] = None, stop_on_error: bool = False):
    request_id = set_request_id()
    info_id(f"[{request_id}] Loading workbook: {xlsx_path}")

    xl = pd.ExcelFile(xlsx_path)
    sheet_order = ["Campus", "Building","Site", "Area", "EquipmentGroup", "Model", "AssetNumber", "Location", "Position"]

    to_process = sheet_order if not only else [s for s in sheet_order if s in (only or [])]
    info_id(f"Sheets to process: {to_process}")

    cache = Cache()

    for sheet_name in to_process:
        if sheet_name not in xl.sheet_names:
            debug_id(f"Sheet '{sheet_name}' not present in workbook; skipping.")
            continue

        if sheet_name not in SHEET_LOADERS:
            debug_id(f"No loader implemented for sheet '{sheet_name}'; skipping.")
            continue

        info_id(f"Processing sheet '{sheet_name}'...")
        df = xl.parse(sheet_name)
        info_id(f"Sheet '{sheet_name}' has {len(df)} rows and columns: {list(df.columns)}")

        loader = SHEET_LOADERS[sheet_name]
        loader(session, df, cache, stop_on_error)

    info_id(f"[{request_id}] Workbook load complete.")


# --- CLI ---
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
        help="Optional database URL"
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
        help=f"Only load specific sheets (choices: {list(SHEET_LOADERS.keys())})"
    )
    p.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately on first row error"
    )
    p.add_argument(
        "--create-tables",
        action="store_true",
        help="Automatically create missing database tables"
    )
    p.add_argument(
        "--check-only",
        action="store_true",
        help="Only check database status, don't load data"
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    return p


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    # Session selection
    if args.db:
        info_id(f"Using DB URL from --db: {args.db}")
        engine = create_engine(args.db, future=True)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
    else:
        info_id("Using default DB session from database_config")
        session = get_main_session()

    try:
        if args.check_only:
            if not check_database_only(session):
                info_id("Database check found issues - see details above.")
                return 1
            else:
                info_id("Database check completed successfully.")
                return 0

        if not prepare_database(session, auto_create=args.create_tables):
            error_id("Database validation failed. Cannot proceed.")
            return 1

        import os
        if not os.path.exists(args.file):
            error_id(f"File not found: {args.file}")
            return 1

        load_workbook(session, args.file, only=args.only, stop_on_error=args.stop_on_error)

        if args.dry_run:
            info_id("Dry-run enabled: rolling back all changes.")
            session.rollback()
        else:
            session.commit()
            info_id("Committed changes to the database.")
        return 0

    except FileNotFoundError as e:
        session.rollback()
        error_id(f"File error: {e}")
        return 1

    except SQLAlchemyError as db_err:
        session.rollback()
        error_id(f"Database error: {db_err}")
        if args.verbose:
            import traceback
            error_id(traceback.format_exc())
        return 1

    except Exception as e:
        session.rollback()
        error_id(f"Fatal error: {e}")
        if args.verbose:
            import traceback
            error_id(traceback.format_exc())
        return 1

    finally:
        try:
            session.close()
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
