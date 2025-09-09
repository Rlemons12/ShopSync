# app/modules/database/loadsheets/loader/check_db_before_load.py
from __future__ import annotations
import sys
import json
from typing import List, Tuple

from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError

# ---- Your project config & DB session
from app.modules.configuration.database_config import DatabaseConfig
from app.modules.configuration.config import DATABASE_URL

# ---- Your ORM models (import only what you have defined)
from app.modules.database.shopsync_db import (
    Base,
    Campus,
    Building,
    SiteLocation,
    Position,
    # If these are defined in your schema, keep them; else comment them out.
    # Container, Shelf, Drawer, DrawerSlot,
    # Part, Inventory,
)

# Tables you expect to exist (ORM classes or table names).
# Mix classes and strings allowed; the inspector will resolve names.
REQUIRED_TABLES: List = [
    Campus, Building, SiteLocation, Position,
    # Container, Shelf, Drawer, DrawerSlot,
    # Part, Inventory,
]

# How many sample rows to show per table
SAMPLE_LIMIT = 5


def _table_name(obj) -> str:
    if hasattr(obj, "__tablename__"):
        return obj.__tablename__
    if hasattr(obj, "__table__"):
        return obj.__table__.name
    if isinstance(obj, str):
        return obj
    return str(obj)


def main() -> int:
    print(f"[INFO] Using DATABASE_URL = {DATABASE_URL}")

    db = DatabaseConfig()
    try:
        # 1) Test connection
        engine = db.engine  # created lazily inside DatabaseConfig
        with engine.connect() as conn:
            version = conn.execute(text("select sqlite_version()")).scalar()
            print(f"[OK] Connected. SQLite version: {version}")

        insp = inspect(engine)
        existing = set(insp.get_table_names())
        print(f"[INFO] Found {len(existing)} tables in DB.")

        # 2) Check required tables exist
        missing: List[str] = []
        required_names: List[str] = [_table_name(t) for t in REQUIRED_TABLES]
        for tname in required_names:
            if tname not in existing:
                missing.append(tname)

        if missing:
            print("[WARN] Missing required tables:")
            for m in missing:
                print(f"  - {m}")
        else:
            print("[OK] All required tables exist.")

        # 3) Row counts + sample rows
        print("\n[INFO] Table status (counts and samples):")
        Session = db.SessionLocal
        s = Session()
        try:
            for tname in sorted(required_names):
                if tname not in existing:
                    continue  # skip missing

                # Count rows via SELECT COUNT(*)
                try:
                    cnt = s.execute(text(f"SELECT COUNT(*) FROM {tname}")).scalar() or 0
                except SQLAlchemyError as e:
                    print(f"[ERROR] Failed counting table {tname}: {e}")
                    cnt = "ERR"

                print(f"\n  - {tname}: {cnt} rows")

                # Sample a few rows as JSON-like dicts (best-effort)
                if isinstance(cnt, int) and cnt > 0:
                    try:
                        rows = s.execute(text(f"SELECT * FROM {tname} LIMIT {SAMPLE_LIMIT}")).mappings().all()
                        # pretty print
                        print("    samples:")
                        for r in rows:
                            print("     ", json.dumps(dict(r), default=str))
                    except SQLAlchemyError as e:
                        print(f"    [ERROR] Failed reading samples from {tname}: {e}")

        finally:
            s.close()

        print("\n[INFO] DB preflight complete.")
        # Non-zero exit if missing critical tables
        return 2 if missing else 0

    except Exception as e:
        print(f"[FATAL] Could not connect or inspect DB: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
