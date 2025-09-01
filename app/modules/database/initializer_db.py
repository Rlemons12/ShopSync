#!/usr/bin/env python3
"""
Interactive initializer for the ShopSync SQLite database.

Runs with no command-line args. Prompts the user for:
- Command: init / inspect / drop
- Echo SQL? (Y/N)
- Enable WAL? (Y/N)
"""

from __future__ import annotations
import os
import sys

# Ensure ShopSync project root is on sys.path when running directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Import the DB manager + models (registers tables)
from app.modules.database.db_manager import ShopSyncDatabase
from app.modules.database import shopsync_db  # noqa: F401  (register models)


def ask(prompt: str, default: str = "") -> str:
    """Prompt user with optional default."""
    resp = input(f"{prompt} [{default}]: ").strip().lower()
    return resp if resp else default


def main() -> None:
    print("=== ShopSync Database Initializer ===")
    command = ask("Command (init / inspect / drop)", "init")
    echo = ask("Echo SQL? (y/n)", "n") == "y"
    wal = ask("Enable WAL mode? (y/n)", "n") == "y"

    db = ShopSyncDatabase(echo=echo, enable_wal=wal)

    if command == "init":
        db.create_all()
        db.print_inspect()
    elif command == "inspect":
        db.print_inspect()
    elif command == "drop":
        db.drop_all()
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
