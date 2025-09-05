
#!/usr/bin/env python3
"""
loader_equipment_relationships_db.py

Load equipment relationships from an Excel workbook into your database.
Covers: Campus (aka BuildingComplex), Building, SiteLocation, Area, EquipmentGroup,
Model, AssetNumber, Location, Subassembly, ComponentAssembly, AssemblyView, Position.

USAGE
-----
# Basic (auto-detect default DB or use your DatabaseConfig if available)
python loader_equipment_relationships_db.py --file path/to/load_equipment_relationships_table_data.xlsx

# Specify DB URL explicitly (overrides config autodetect)
python loader_equipment_relationships_db.py --file path/to.xlsx --db sqlite:///shopsync.db

# Dry run (no writes)
python loader_equipment_relationships_db.py --file path/to.xlsx --dry-run

# Load only some sheets
python loader_equipment_relationships_db.py --file path/to.xlsx --only Campus,Building,SiteLocation

# Stop on first sheet error
python loader_equipment_relationships_db.py --file path/to.xlsx --stop-on-error

NOTES
-----
- If your codebase defines logging helpers (info_id/debug_id/error_id) and request IDs,
  this script will use them. Otherwise it falls back to standard logging.
- It tries to import your models from `shopsync_db` first. If your project uses a different
  path (e.g., `app.modules.database.shopsync_db`), update the IMPORT SECTION below.
- Sheet name "Campus" maps to the model class `BuildingComplex` (legacy table `buildingComplex`).
- If your `SiteLocation` requires non-null room_number/site_area, provide them in the sheet.
- The loader is idempotent: re-running does not duplicate rows.
"""

import argparse
import logging
import sys
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, Any, List

# 3rd-party
import pandas as pd

# ---------------------------------------------------------------------------
# IMPORT SECTION: Models & (optional) DatabaseConfig
# ---------------------------------------------------------------------------
# This block tries multiple common import paths. Adjust if your project differs.
Base = None
DatabaseConfig = None
Position = None

# Individual model classes we need
BuildingComplex = None  # Campus
Campus = None           # if you renamed class
Building = None
SiteLocation = None
Area = None
EquipmentGroup = None
Model = None
AssetNumber = None
Location = None
Subassembly = None
ComponentAssembly = None
AssemblyView = None

_import_errors: List[str] = []

def _try_imports():
    global Base, DatabaseConfig, Position
    global BuildingComplex, Campus, Building, SiteLocation, Area, EquipmentGroup, Model
    global AssetNumber, Location, Subassembly, ComponentAssembly, AssemblyView

    candidates = [
        # Most typical: file named shopsync_db.py importable on PYTHONPATH
        ("shopsync_db", [
            "Base", "Position", "BuildingComplex", "Building", "SiteLocation", "Area",
            "EquipmentGroup", "Model", "AssetNumber", "Location", "Subassembly",
            "ComponentAssembly", "AssemblyView", "Campus"
        ]),
        # Alternative: nested module path (adjust as needed)
        ("app.modules.database.shopsync_db", [
            "Base", "Position", "BuildingComplex", "Building", "SiteLocation", "Area",
            "EquipmentGroup", "Model", "AssetNumber", "Location", "Subassembly",
            "ComponentAssembly", "AssemblyView", "Campus"
        ]),
    ]

    # Optional DatabaseConfig from your config module(s)
    dbconfig_candidates = [
        ("modules.configuration.config", ["DatabaseConfig"]),
        ("app.modules.configuration.config", ["DatabaseConfig"]),
        ("modules.configuration.database_config", ["DatabaseConfig"]),
        ("app.modules.configuration.database_config", ["DatabaseConfig"]),
    ]

    # Try to import models
    imported = False
    for mod_name, names in candidates:
        try:
            mod = __import__(mod_name, fromlist=names)
            Base = getattr(mod, "Base", Base)
            Position = getattr(mod, "Position", Position)
            # Pull entity classes if present
            for nm in names:
                if nm in ("Base", "Position"):
                    continue
                if hasattr(mod, nm):
                    globals()[nm] = getattr(mod, nm)
            imported = True
            break
        except Exception as e:
            _import_errors.append(f"{mod_name}: {e!r}")
            continue

    # Try to import DatabaseConfig
    for mod_name, names in dbconfig_candidates:
        try:
            mod = __import__(mod_name, fromlist=names)
            DatabaseConfig = getattr(mod, "DatabaseConfig")
            break
        except Exception as e:
            _import_errors.append(f"{mod_name}: {e!r}")
            continue

    if not imported:
        raise ImportError(
            "Could not import models from shopsync_db. "
            "Tried:\n  - " + "\n  - ".join(_import_errors)
        )

_try_imports()

# If the project renamed BuildingComplex to Campus (class name), prefer it.
CampusModel = Campus if Campus is not None else BuildingComplex

# ---------------------------------------------------------------------------
# Logging helpers (try your project's wrappers, else fallback)
# ---------------------------------------------------------------------------
try:
    from modules.configuration.log_config import info_id, debug_id, error_id, set_request_id, get_request_id
except Exception:
    try:
        from app.modules.configuration.log_config import info_id, debug_id, error_id, set_request_id, get_request_id
    except Exception:
        # Fallback minimal wrappers
        _logger = logging.getLogger("loader")
        _handler = logging.StreamHandler(sys.stdout)
        _formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        _handler.setFormatter(_formatter)
        if not _logger.handlers:
            _logger.addHandler(_handler)
        _logger.setLevel(logging.INFO)

        _REQ_ID = None

        def set_request_id(req_id: Optional[str] = None):
            """Fallback: set a request id (or generate one)."""
            nonlocal_vars = globals()
            rid = req_id or f"REQ-{uuid.uuid4().hex[:8]}"
            nonlocal_vars["_REQ_ID"] = rid
            return rid

        def get_request_id() -> str:
            return globals().get("_REQ_ID") or "REQ-UNKNOWN"

        def info_id(msg: str, request_id: Optional[str] = None):
            rid = request_id or get_request_id()
            _logger.info(f"[{rid}] {msg}")

        def debug_id(msg: str, request_id: Optional[str] = None):
            rid = request_id or get_request_id()
            _logger.debug(f"[{rid}] {msg}")

        def error_id(msg: str, request_id: Optional[str] = None):
            rid = request_id or get_request_id()
            _logger.error(f"[{rid}] {msg}")

# ---------------------------------------------------------------------------
# SQLAlchemy Session setup
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def _session_factory_from_dburl(db_url: str):
    engine = create_engine(db_url, future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

def _session_factory_from_config():
    """If DatabaseConfig is available, use it to acquire the main session factory."""
    if DatabaseConfig is None:
        return None
    try:
        cfg = DatabaseConfig()
        # Prefer any explicit session factory if provided by your config
        if hasattr(cfg, "get_main_sessionmaker"):
            return cfg.get_main_sessionmaker()
        if hasattr(cfg, "get_main_session"):
            # Wrap into sessionmaker-like factory
            sess = cfg.get_main_session()
            # create a tiny factory that always yields a fresh Session from cfg
            def _factory():
                return cfg.get_main_session()
            class _Factory:
                def __call__(self):  # mimic sessionmaker interface
                    return _factory()
            return _Factory()
    except Exception as e:
        error_id(f"DatabaseConfig session factory error: {e!r}")
        return None

    return None

@contextmanager
def session_scope(SessionFactory):
    """Provide a transactional scope around a series of operations."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        raise
    finally:
        session.close()

# ---------------------------------------------------------------------------
# Data normalization helpers
# ---------------------------------------------------------------------------
def norm_str(val: Any) -> Optional[str]:
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s else None

def key_lower(*parts: Any) -> Tuple:
    """Build a case-insensitive cache key from parts (strings or None)."""
    out = []
    for p in parts:
        if p is None:
            out.append(None)
        else:
            out.append(str(p).strip().lower())
    return tuple(out)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
@dataclass
class Cache:
    campus: Dict[Tuple, int]
    building: Dict[Tuple, int]
    site_location: Dict[Tuple, int]
    area: Dict[Tuple, int]
    equipment_group: Dict[Tuple, int]
    model: Dict[Tuple, int]
    asset_number: Dict[Tuple, int]
    location: Dict[Tuple, int]
    subassembly: Dict[Tuple, int]
    component_assembly: Dict[Tuple, int]
    assembly_view: Dict[Tuple, int]

    def __init__(self):
        self.campus = {}
        self.building = {}
        self.site_location = {}
        self.area = {}
        self.equipment_group = {}
        self.model = {}
        self.asset_number = {}
        self.location = {}
        self.subassembly = {}
        self.component_assembly = {}
        self.assembly_view = {}

# ---------------------------------------------------------------------------
# Get-or-create helpers per entity
# ---------------------------------------------------------------------------
def get_or_create_campus(session, cache: Cache, name: str, **extra) -> int:
    k = key_lower(name)
    if k in cache.campus:
        return cache.campus[k]
    obj = session.query(CampusModel).filter(CampusModel.name.ilike(name)).one_or_none()
    if obj is None:
        obj = CampusModel(name=name,
                          description=extra.get("description"),
                          city=extra.get("city"),
                          state=extra.get("state"),
                          country=extra.get("country"))
        session.add(obj)
        session.flush()
        info_id(f"Created Campus '{name}' (id={obj.id})")
    cache.campus[k] = obj.id
    return obj.id

def get_or_create_building(session, cache: Cache, name: str, campus_name: str, **extra) -> int:
    ck = key_lower(campus_name)
    campus_id = cache.campus.get(ck)
    if campus_id is None:
        # fallback DB look-up
        camp = session.query(CampusModel).filter(CampusModel.name.ilike(campus_name)).one_or_none()
        if not camp:
            raise ValueError(f"Unknown Campus '{campus_name}' for Building '{name}'")
        campus_id = camp.id
        cache.campus[ck] = campus_id

    k = key_lower(name, campus_name)
    if k in cache.building:
        return cache.building[k]

    # shopsync_db.Building uses id_building_complex FK to buildingComplex (Campus)
    obj = (session.query(Building)
                 .filter(Building.name.ilike(name),
                         Building.id_building_complex == campus_id)
                 .one_or_none())
    if obj is None:
        obj = Building(name=name,
                       description=extra.get("description"),
                       address=extra.get("address"),
                       id_building_complex=campus_id)
        session.add(obj)
        session.flush()
        info_id(f"Created Building '{name}' in Campus '{campus_name}' (id={obj.id})")
    cache.building[k] = obj.id
    return obj.id

def get_or_create_site_location(session, cache: Cache, title: str, building_name: str,
                                room_number: Optional[str] = None,
                                site_area: Optional[str] = None) -> int:
    # Ensure building exists
    bkey = key_lower(building_name)
    building_id = cache.building.get(bkey)
    if building_id is None:
        bobj = session.query(Building).filter(Building.name.ilike(building_name)).one_or_none()
        if not bobj:
            raise ValueError(f"Unknown Building '{building_name}' for SiteLocation '{title}'")
        building_id = bobj.id
        cache.building[bkey] = building_id

    # SiteLocation has non-null title, room_number, site_area in current schema
    room_number = room_number or "UNKNOWN"
    site_area = site_area or "UNKNOWN"

    k = key_lower(title, building_name, room_number, site_area)
    if k in cache.site_location:
        return cache.site_location[k]

    obj = (session.query(SiteLocation)
                 .filter(SiteLocation.title.ilike(title),
                         SiteLocation.building_id == building_id,
                         SiteLocation.room_number == room_number,
                         SiteLocation.site_area == site_area)
                 .one_or_none())
    if obj is None:
        obj = SiteLocation(title=title,
                           room_number=room_number,
                           site_area=site_area,
                           building_id=building_id)
        session.add(obj)
        session.flush()
        info_id(f"Created SiteLocation '{title}' (room={room_number}, area={site_area}) in Building '{building_name}' (id={obj.id})")
    cache.site_location[k] = obj.id
    return obj.id

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

def get_or_create_equipment_group(session, cache: Cache, name: str, area_name: str,
                                  description: Optional[str] = None) -> int:
    area_id = get_or_create_area(session, cache, area_name)
    k = key_lower(name, area_name)
    if k in cache.equipment_group:
        return cache.equipment_group[k]
    obj = (session.query(EquipmentGroup)
                 .filter(EquipmentGroup.name.ilike(name),
                         EquipmentGroup.area_id == area_id)
                 .one_or_none())
    if obj is None:
        obj = EquipmentGroup(name=name, area_id=area_id, description=description)
        session.add(obj)
        session.flush()
        info_id(f"Created EquipmentGroup '{name}' under Area '{area_name}' (id={obj.id})")
    cache.equipment_group[k] = obj.id
    return obj.id

def get_or_create_model(session, cache: Cache, name: str, equipment_group_name: str,
                        description: Optional[str] = None) -> int:
    eg_id = get_or_create_equipment_group(session, cache, equipment_group_name, None)
    k = key_lower(name, equipment_group_name)
    if k in cache.model:
        return cache.model[k]
    obj = (session.query(Model)
                 .filter(Model.name.ilike(name),
                         Model.equipment_group_id == eg_id)
                 .one_or_none())
    if obj is None:
        obj = Model(name=name, equipment_group_id=eg_id, description=description)
        session.add(obj)
        session.flush()
        info_id(f"Created Model '{name}' under EquipmentGroup '{equipment_group_name}' (id={obj.id})")
    cache.model[k] = obj.id
    return obj.id

def get_or_create_asset_number(session, cache: Cache, number: str, model_name: str,
                               description: Optional[str] = None) -> int:
    model_id = get_or_create_model(session, cache, model_name, equipment_group_name=cache_eg_name_from_model_name(session, cache, model_name))
    # However, the helper above expects equipment_group_name. If we don't have it, we do a DB lookup
    # by model_name only to find the single model, else require explicit EG name to avoid ambiguity.
    # Let's simplify: find model by name ignoring EG cache.
    model_obj = session.query(Model).filter(Model.name.ilike(model_name)).one_or_none()
    if not model_obj:
        raise ValueError(f"Model '{model_name}' not found when creating AssetNumber '{number}'")
    model_id = model_obj.id

    k = key_lower(number, model_name)
    if k in cache.asset_number:
        return cache.asset_number[k]
    obj = (session.query(AssetNumber)
                 .filter(AssetNumber.number.ilike(number),
                         AssetNumber.model_id == model_id)
                 .one_or_none())
    if obj is None:
        obj = AssetNumber(number=number, model_id=model_id, description=description)
        session.add(obj)
        session.flush()
        info_id(f"Created AssetNumber '{number}' under Model '{model_name}' (id={obj.id})")
    cache.asset_number[k] = obj.id
    return obj.id

def get_or_create_location(session, cache: Cache, name: str, model_name: str,
                           description: Optional[str] = None) -> int:
    model_obj = session.query(Model).filter(Model.name.ilike(model_name)).one_or_none()
    if not model_obj:
        raise ValueError(f"Model '{model_name}' not found when creating Location '{name}'")
    k = key_lower(name, model_name)
    if k in cache.location:
        return cache.location[k]
    obj = (session.query(Location)
                 .filter(Location.name.ilike(name),
                         Location.model_id == model_obj.id)
                 .one_or_none())
    if obj is None:
        obj = Location(name=name, model_id=model_obj.id, description=description)
        session.add(obj)
        session.flush()
        info_id(f"Created Location '{name}' under Model '{model_name}' (id={obj.id})")
    cache.location[k] = obj.id
    return obj.id

def get_or_create_subassembly(session, cache: Cache, name: Optional[str], location_name: str,
                              model_name: Optional[str] = None,
                              description: Optional[str] = None) -> int:
    # find Location (needs name + model_name ideally; but allow unique name)
    loc_obj = None
    if model_name:
        loc_obj = (session.query(Location)
                         .join(Model, Location.model_id == Model.id)
                         .filter(Location.name.ilike(location_name),
                                 Model.name.ilike(model_name))
                         .one_or_none())
    if loc_obj is None:
        # fallback by location name only
        loc_obj = session.query(Location).filter(Location.name.ilike(location_name)).one_or_none()
    if not loc_obj:
        raise ValueError(f"Location '{location_name}' not found for Subassembly '{name or 'NULL'}'")

    # name can be nullable; normalize missing name
    name = name or f"{location_name}::subassembly"

    k = key_lower(name, location_name, model_name or "")
    if k in cache.subassembly:
        return cache.subassembly[k]

    obj = (session.query(Subassembly)
                 .filter(Subassembly.name.ilike(name),
                         Subassembly.location_id == loc_obj.id)
                 .one_or_none())
    if obj is None:
        obj = Subassembly(name=name, location_id=loc_obj.id, description=description)
        session.add(obj)
        session.flush()
        info_id(f"Created Subassembly '{name}' under Location '{location_name}' (id={obj.id})")
    cache.subassembly[k] = obj.id
    return obj.id

def get_or_create_component_assembly(session, cache: Cache, name: Optional[str], subassembly_name: str) -> int:
    # find subassembly by name (assume unique or previously created in this run)
    sub_obj = session.query(Subassembly).filter(Subassembly.name.ilike(subassembly_name)).one_or_none()
    if not sub_obj:
        raise ValueError(f"Subassembly '{subassembly_name}' not found for ComponentAssembly '{name or 'NULL'}'")
    name = name or f"{subassembly_name}::component"
    k = key_lower(name, subassembly_name)
    if k in cache.component_assembly:
        return cache.component_assembly[k]
    obj = (session.query(ComponentAssembly)
                 .filter(ComponentAssembly.name.ilike(name),
                         ComponentAssembly.subassembly_id == sub_obj.id)
                 .one_or_none())
    if obj is None:
        obj = ComponentAssembly(name=name, subassembly_id=sub_obj.id)
        session.add(obj)
        session.flush()
        info_id(f"Created ComponentAssembly '{name}' under Subassembly '{subassembly_name}' (id={obj.id})")
    cache.component_assembly[k] = obj.id
    return obj.id

def get_or_create_assembly_view(session, cache: Cache, name: Optional[str], component_assembly_name: str) -> int:
    comp_obj = session.query(ComponentAssembly).filter(ComponentAssembly.name.ilike(component_assembly_name)).one_or_none()
    if not comp_obj:
        raise ValueError(f"ComponentAssembly '{component_assembly_name}' not found for AssemblyView '{name or 'NULL'}'")
    name = name or f"{component_assembly_name}::view"
    k = key_lower(name, component_assembly_name)
    if k in cache.assembly_view:
        return cache.assembly_view[k]
    obj = (session.query(AssemblyView)
                 .filter(AssemblyView.name.ilike(name),
                         AssemblyView.component_assembly_id == comp_obj.id)
                 .one_or_none())
    if obj is None:
        obj = AssemblyView(name=name, component_assembly_id=comp_obj.id)
        session.add(obj)
        session.flush()
        info_id(f"Created AssemblyView '{name}' under ComponentAssembly '{component_assembly_name}' (id={obj.id})")
    cache.assembly_view[k] = obj.id
    return obj.id

def get_or_create_position(session, ids: dict) -> int:
    """Get or create a Position row with the exact set of FKs provided in ids dict.
       ids may contain any subset of:
       area_id, equipment_group_id, model_id, asset_number_id, location_id, subassembly_id,
       component_assembly_id, assembly_view_id, site_location_id, building_id, building_complex (id)
    """
    filters = {}
    for k in ["area_id", "equipment_group_id", "model_id", "asset_number_id", "location_id",
              "subassembly_id", "component_assembly_id", "assembly_view_id",
              "site_location_id", "building_id", "building_complex"]:
        filters[k] = ids.get(k)

    query = session.query(Position).filter_by(**filters)
    obj = query.one_or_none()
    if obj is None:
        obj = Position(**filters)
        session.add(obj)
        session.flush()
        info_id(f"Created Position id={obj.id} with FKs: " +
                ", ".join(f"{k}={v}" for k, v in filters.items() if v is not None))
    else:
        debug_id(f"Reused existing Position id={obj.id}")
    return obj.id

# Helper: try to infer EG name from model name (if unique). Used in asset creation path.
def cache_eg_name_from_model_name(session, cache: Cache, model_name: str) -> Optional[str]:
    # First check cache by scanning model entries
    for (m_name, eg_name), _id in cache.model.items():
        if m_name == model_name.strip().lower():
            return eg_name
    # Fallback to DB: find model and join equipment group
    m = (session.query(Model, EquipmentGroup)
               .join(EquipmentGroup, Model.equipment_group_id == EquipmentGroup.id)
               .filter(Model.name.ilike(model_name))
               .one_or_none())
    if m:
        return m[1].name
    return None

# ---------------------------------------------------------------------------
# Per-sheet loaders
# ---------------------------------------------------------------------------
def require_columns(df: pd.DataFrame, required: List[str], sheet_name: str):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Sheet '{sheet_name}' is missing required columns: {missing}")

def load_campus_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="Campus"):
    # columns: name*, description, city, state, country
    require_columns(df, ["name"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        name = norm_str(row.get("name"))
        if not name:
            debug_id(f"Skipping Campus row with blank name")
            continue
        extra = {
            "description": norm_str(row.get("description")),
            "city": norm_str(row.get("city")),
            "state": norm_str(row.get("state")),
            "country": norm_str(row.get("country")),
        }
        get_or_create_campus(session, cache, name, **extra)
        created += 1
    return created

def load_building_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="Building"):
    # columns: name*, CampusName*, description, address
    # accept alias "BuildingComplexName" as CampusName
    aliases = {"BuildingComplexName": "CampusName"}
    for a, b in aliases.items():
        if a in df.columns and b not in df.columns:
            df[b] = df[a]

    require_columns(df, ["name", "CampusName"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        name = norm_str(row.get("name"))
        campus_name = norm_str(row.get("CampusName"))
        if not name or not campus_name:
            debug_id(f"Skipping Building row with missing name or CampusName")
            continue
        extra = {
            "description": norm_str(row.get("description")),
            "address": norm_str(row.get("address")),
        }
        get_or_create_building(session, cache, name, campus_name, **extra)
        created += 1
    return created

def load_site_location_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="SiteLocation"):
    # columns: title*, BuildingName*, room_number, site_area
    require_columns(df, ["title", "BuildingName"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        title = norm_str(row.get("title"))
        building_name = norm_str(row.get("BuildingName"))
        room_number = norm_str(row.get("room_number"))
        site_area = norm_str(row.get("site_area"))
        if not title or not building_name:
            debug_id(f"Skipping SiteLocation row with missing title or BuildingName")
            continue
        get_or_create_site_location(session, cache, title, building_name, room_number, site_area)
        created += 1
    return created

def load_area_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="Area"):
    # columns: name*, description
    require_columns(df, ["name"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        name = norm_str(row.get("name"))
        description = norm_str(row.get("description"))
        if not name:
            continue
        get_or_create_area(session, cache, name, description)
        created += 1
    return created

def load_equipment_group_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="EquipmentGroup"):
    # columns: name*, AreaName*, description
    require_columns(df, ["name", "AreaName"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        name = norm_str(row.get("name"))
        area_name = norm_str(row.get("AreaName"))
        description = norm_str(row.get("description"))
        if not name or not area_name:
            continue
        get_or_create_equipment_group(session, cache, name, area_name, description)
        created += 1
    return created

def load_model_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="Model"):
    # columns: name*, EquipmentGroupName*, description
    require_columns(df, ["name", "EquipmentGroupName"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        name = norm_str(row.get("name"))
        eg_name = norm_str(row.get("EquipmentGroupName"))
        description = norm_str(row.get("description"))
        if not name or not eg_name:
            continue
        get_or_create_model(session, cache, name, eg_name, description)
        created += 1
    return created

def load_asset_number_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="AssetNumber"):
    # columns: number*, ModelName*, description
    require_columns(df, ["number", "ModelName"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        number = norm_str(row.get("number"))
        model_name = norm_str(row.get("ModelName"))
        description = norm_str(row.get("description"))
        if not number or not model_name:
            continue
        get_or_create_asset_number(session, cache, number, model_name, description)
        created += 1
    return created

def load_location_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="Location"):
    # columns: name*, ModelName*, description
    require_columns(df, ["name", "ModelName"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        name = norm_str(row.get("name"))
        model_name = norm_str(row.get("ModelName"))
        description = norm_str(row.get("description"))
        if not name or not model_name:
            continue
        get_or_create_location(session, cache, name, model_name, description)
        created += 1
    return created

def load_subassembly_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="Subassembly"):
    # columns: name (optional), LocationName*, ModelName (optional), description (optional)
    require_columns(df, ["LocationName"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        name = norm_str(row.get("name"))
        location_name = norm_str(row.get("LocationName"))
        model_name = norm_str(row.get("ModelName"))
        description = norm_str(row.get("description"))
        if not location_name:
            continue
        get_or_create_subassembly(session, cache, name, location_name, model_name, description)
        created += 1
    return created

def load_component_assembly_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="ComponentAssembly"):
    # columns: name (optional), SubassemblyName*
    require_columns(df, ["SubassemblyName"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        name = norm_str(row.get("name"))
        subassembly_name = norm_str(row.get("SubassemblyName"))
        if not subassembly_name:
            continue
        get_or_create_component_assembly(session, cache, name, subassembly_name)
        created += 1
    return created

def load_assembly_view_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="AssemblyView"):
    # columns: name (optional), ComponentAssemblyName*
    require_columns(df, ["ComponentAssemblyName"], sheet_name)
    created = 0
    for _, row in df.iterrows():
        name = norm_str(row.get("name"))
        comp_name = norm_str(row.get("ComponentAssemblyName"))
        if not comp_name:
            continue
        get_or_create_assembly_view(session, cache, name, comp_name)
        created += 1
    return created

def load_position_sheet(session, cache: Cache, df: pd.DataFrame, sheet_name="Position"):
    # Flexible: resolve any combination of the following columns:
    # AreaName, EquipmentGroupName, ModelName, AssetNumber, LocationName, SubassemblyName,
    # ComponentAssemblyName, AssemblyViewName, SiteLocationTitle
    created = 0
    for _, row in df.iterrows():
        ids = {}

        area_name = norm_str(row.get("AreaName"))
        eg_name = norm_str(row.get("EquipmentGroupName"))
        model_name = norm_str(row.get("ModelName"))
        asset_num = norm_str(row.get("AssetNumber"))
        location_name = norm_str(row.get("LocationName"))
        sub_name = norm_str(row.get("SubassemblyName"))
        comp_name = norm_str(row.get("ComponentAssemblyName"))
        view_name = norm_str(row.get("AssemblyViewName"))
        sl_title = norm_str(row.get("SiteLocationTitle"))
        building_name = norm_str(row.get("BuildingName"))  # optional, used if you want to set building_id too
        campus_name = norm_str(row.get("CampusName"))      # optional, used if you want to set building_complex

        if area_name:
            ids["area_id"] = get_or_create_area(session, cache, area_name)
        if eg_name:
            ids["equipment_group_id"] = get_or_create_equipment_group(session, cache, eg_name, area_name or "")
        if model_name:
            # If eg_name is provided, we already ensured (model, eg)
            ids["model_id"] = get_or_create_model(session, cache, model_name, eg_name or "")
        if asset_num:
            if not model_name:
                raise ValueError(f"Position row with AssetNumber '{asset_num}' requires ModelName")
            ids["asset_number_id"] = get_or_create_asset_number(session, cache, asset_num, model_name)
        if location_name:
            if not model_name:
                raise ValueError(f"Position row with LocationName '{location_name}' requires ModelName")
            ids["location_id"] = get_or_create_location(session, cache, location_name, model_name)
        if sub_name:
            # If model_name provided, better disambiguation
            ids["subassembly_id"] = get_or_create_subassembly(session, cache, sub_name, location_name or "", model_name)
        if comp_name:
            ids["component_assembly_id"] = get_or_create_component_assembly(session, cache, comp_name, sub_name or "")
        if view_name:
            ids["assembly_view_id"] = get_or_create_assembly_view(session, cache, view_name, comp_name or "")
        if sl_title:
            # building name required to uniquely resolve site location (by our loader design)
            bname = building_name or ""
            if not bname:
                debug_id(f"Position row uses SiteLocationTitle '{sl_title}' without BuildingName; loader will search by title only.")
                sl_obj = session.query(SiteLocation).filter(SiteLocation.title.ilike(sl_title)).one_or_none()
                if not sl_obj:
                    raise ValueError(f"SiteLocation '{sl_title}' not found; include BuildingName in Position sheet if multiple exist.")
                ids["site_location_id"] = sl_obj.id
            else:
                ids["site_location_id"] = get_or_create_site_location(session, cache, sl_title, bname)
        if building_name:
            # optional: also set building_id on Position
            bobj = session.query(Building).filter(Building.name.ilike(building_name)).one_or_none()
            if bobj:
                ids["building_id"] = bobj.id
        if campus_name:
            cobj = session.query(CampusModel).filter(CampusModel.name.ilike(campus_name)).one_or_none()
            if cobj:
                # Column name in Position is 'building_complex' (int FK id)
                ids["building_complex"] = cobj.id

        get_or_create_position(session, ids)
        created += 1
    return created

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
SHEET_ORDER = [
    "Campus",            # maps to BuildingComplex model
    "Building",
    "SiteLocation",
    "Area",
    "EquipmentGroup",
    "Model",
    "AssetNumber",
    "Location",
    "Subassembly",
    "ComponentAssembly",
    "AssemblyView",
    "Position",
]

# For backwards compatibility if workbook uses legacy sheet names
SHEET_ALIASES = {
    "BuildingComplex": "Campus",
}

LOADERS = {
    "Campus": load_campus_sheet,
    "Building": load_building_sheet,
    "SiteLocation": load_site_location_sheet,
    "Area": load_area_sheet,
    "EquipmentGroup": load_equipment_group_sheet,
    "Model": load_model_sheet,
    "AssetNumber": load_asset_number_sheet,
    "Location": load_location_sheet,
    "Subassembly": load_subassembly_sheet,
    "ComponentAssembly": load_component_assembly_sheet,
    "AssemblyView": load_assembly_view_sheet,
    "Position": load_position_sheet,
}

def determine_session_factory(args) -> Any:
    # 1) if args.db provided -> use it
    if args.db:
        info_id(f"Using DB URL from CLI: {args.db}")
        return _session_factory_from_dburl(args.db)

    # 2) else try DatabaseConfig from your project
    sess_factory = _session_factory_from_config()
    if sess_factory:
        info_id("Using DatabaseConfig session factory")
        return sess_factory

    # 3) fallback: local sqlite file in current directory
    fallback = "sqlite:///shopsync.db"
    info_id(f"Falling back to default DB URL: {fallback}")
    return _session_factory_from_dburl(fallback)

def main():
    ap = argparse.ArgumentParser(description="Load equipment relationships workbook into DB.")
    ap.add_argument("--file", "-f", required=True, help="Path to Excel workbook")
    ap.add_argument("--db", help="SQLAlchemy DB URL (overrides DatabaseConfig)")
    ap.add_argument("--dry-run", action="store_true", help="Parse/resolve but do not write")
    ap.add_argument("--only", help="Comma-separated list of sheets to load (in dependency order)")
    ap.add_argument("--stop-on-error", action="store_true", help="Stop on first sheet error")
    args = ap.parse_args()

    # Set a request id for consistent logging
    rid = set_request_id()

    # Read workbook (all sheets)
    info_id(f"Reading workbook: {args.file}")
    xls = pd.read_excel(args.file, sheet_name=None)  # dict of {sheet_name: DataFrame}

    # Normalize sheet names (apply aliases)
    sheets = {}
    for name, df in xls.items():
        canonical = SHEET_ALIASES.get(name, name)
        sheets[canonical] = df

    # Determine which sheets to process
    if args.only:
        requested = [s.strip() for s in args.only.split(",") if s.strip()]
        # preserve dependency order but filter to requested
        ordered = [s for s in SHEET_ORDER if s in requested]
        # Also allow loading sheets not in SHEET_ORDER (append at end)
        extras = [s for s in requested if s not in SHEET_ORDER]
        load_sequence = ordered + extras
    else:
        # Use default order but only if present in workbook
        load_sequence = [s for s in SHEET_ORDER if s in sheets]

    if not load_sequence:
        error_id("No known sheets found to load. Check workbook sheet names.")
        sys.exit(2)

    # Session factory and cache
    SessionFactory = determine_session_factory(args)
    cache = Cache()

    summary = {}
    any_error = False

    for sheet_name in load_sequence:
        if sheet_name not in LOADERS:
            debug_id(f"Skipping unknown sheet '{sheet_name}'")
            continue
        if sheet_name not in sheets:
            debug_id(f"Workbook missing sheet '{sheet_name}', skipping.")
            continue

        df = sheets[sheet_name].copy()
        # Trim column names
        df.columns = [c.strip() for c in df.columns]

        loader_fn = LOADERS[sheet_name]
        info_id(f"=== Loading sheet: {sheet_name} (rows={len(df)}) ===")

        if args.dry_run:
            # Just validate required columns; do FK lookups to surface issues, but rollback at end
            try:
                with session_scope(SessionFactory) as session:
                    # Start a SAVEPOINT-like fake dry-run by not committing (we'll rollback via exception)
                    created = loader_fn(session, cache, df, sheet_name=sheet_name)
                    summary[sheet_name] = created
                    # Force rollback by raising
                    raise RuntimeError("DRY_RUN_ABORT")
            except RuntimeError as ex:
                if str(ex) != "DRY_RUN_ABORT":
                    error_id(f"[DRY RUN] Error in sheet '{sheet_name}': {ex}")
                    any_error = True
                    if args.stop_on_error:
                        break
                else:
                    info_id(f"[DRY RUN] Completed validation for sheet '{sheet_name}'")
            except Exception as ex:
                error_id(f"[DRY RUN] Error in sheet '{sheet_name}': {ex}")
                any_error = True
                if args.stop_on_error:
                    break
        else:
            try:
                with session_scope(SessionFactory) as session:
                    created = loader_fn(session, cache, df, sheet_name=sheet_name)
                    summary[sheet_name] = created
            except Exception as ex:
                error_id(f"Error in sheet '{sheet_name}': {ex}")
                any_error = True
                if args.stop_on_error:
                    break

    # Print summary
    info_id("=== Load Summary ===")
    for k, v in summary.items():
        info_id(f"{k}: processed {v} rows")

    if any_error:
        error_id("Completed with errors.")
        sys.exit(1)
    else:
        info_id("Completed successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
