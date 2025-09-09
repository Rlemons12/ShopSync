#!/usr/bin/env python3
"""
Simple database table checker for ShopSync loader.
Just checks what tables exist - no creation, no modification.
"""

import sys
import os
from typing import Dict, List
from sqlalchemy import inspect

# Import your database config
from app.modules.configuration.database_config import DatabaseConfig


def check_database_tables(db_path: str = None) -> Dict[str, bool]:
    """Check which required tables exist in the database."""

    # Tables that the loader will need
    required_tables = [
        'campus',
        'building',
        'site_location',
        'area',
        'equipment_group',
        'model',
        'asset_number',
        'location',
        'position',
        'subassembly',
        'component_assembly',
        'assembly_view',
        'container',
        'shelf',
        'drawer',
        'drawer_slot',
        'part',
        'inventory',
        'drawing',
        'image',
    ]

    # Use specific database path if provided
    if db_path:
        db_url = f"sqlite:///{db_path}"
        db_config = DatabaseConfig(db_url=db_url)
    else:
        db_config = DatabaseConfig()

    print(f"Checking database: {db_config.settings.db_url}")

    # Check if the file actually exists for SQLite
    if db_config.settings.db_url.startswith("sqlite:///"):
        db_file_path = db_config.settings.db_url.replace("sqlite:///", "")
        if os.path.exists(db_file_path):
            print(f"Database file exists: {db_file_path}")
        else:
            print(f"WARNING: Database file does not exist: {db_file_path}")

    print("-" * 50)

    # Get existing tables
    inspector = inspect(db_config.get_engine())
    existing_tables = inspector.get_table_names()

    print(f"Found {len(existing_tables)} tables in database:")
    for table in sorted(existing_tables):
        print(f"  - {table}")

    print("\n" + "-" * 50)
    print("Required tables for loader:")

    table_status = {}
    missing_tables = []
    present_tables = []

    for table_name in required_tables:
        exists = table_name in existing_tables
        table_status[table_name] = exists

        if exists:
            present_tables.append(table_name)
            print(f"  [OK]      {table_name}")
        else:
            missing_tables.append(table_name)
            print(f"  [MISSING] {table_name}")

    print("\n" + "=" * 50)
    print(f"SUMMARY:")
    print(f"  Present: {len(present_tables)}/{len(required_tables)} tables")
    print(f"  Missing: {len(missing_tables)} tables")

    if missing_tables:
        print(f"\nMissing tables: {', '.join(missing_tables)}")
        print("\nTo create missing tables, run:")
        if db_path:
            print(
                f"  python -c \"from app.modules.configuration.database_config import DatabaseConfig; DatabaseConfig(db_url='sqlite:///{db_path}').create_all()\"")
        else:
            print(
                "  python -c \"from app.modules.configuration.database_config import DatabaseConfig; DatabaseConfig().create_all()\"")
    else:
        print("\nAll required tables are present!")

    return table_status


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Check ShopSync database tables")
    parser.add_argument("--db-path", help="Full path to the database file")
    args = parser.parse_args()

    try:
        # Use the specific database path if provided
        db_path = args.db_path or r"C:\Users\10169062\PycharmProjects\ShopSync\app\modules\database\shopsync.db"

        table_status = check_database_tables(db_path)

        # Exit with error code if tables are missing
        missing_count = len([t for t, exists in table_status.items() if not exists])
        return 0 if missing_count == 0 else 1

    except Exception as e:
        print(f"Error checking database: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())