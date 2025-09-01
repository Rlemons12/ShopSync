import re
import sys
from pathlib import Path
from shutil import copy2

def read_text_safely(p: Path) -> str:
    """Try common encodings, then fall back to lossy decode."""
    encodings = ["utf-8", "utf-8-sig", "cp1252"]
    for enc in encodings:
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    # last resort: lossy decode so we can still operate
    return p.read_bytes().decode("utf-8", errors="ignore")

def write_text_utf8(p: Path, text: str) -> None:
    p.write_text(text, encoding="utf-8", newline="\n")

def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("shopsync_db.py")
    if not target.exists():
        print(f"ERROR: {target} not found. Pass the correct path as an argument.")
        sys.exit(1)

    src = read_text_safely(target)

    # ---------- 1) Remove Flask import block entirely ----------
    src = re.sub(
        r"\n?# Optional:\s*Flask's g.*?try:\s*from flask import g\s*except ImportError:\s*g\s*=\s*None\s*",
        "\n# Flask dependency removed; request_id is provided via @with_request_id\n",
        src,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # ---------- 2) Replace request_id=g.request_id -> request_id=request_id ----------
    src = re.sub(r"request_id\s*=\s*g\.request_id", "request_id=request_id", src)

    # ---------- 3) Ensure _get_positions_by_hierarchy has request_id param ----------
    def add_reqid_param(match: re.Match) -> str:
        sig = match.group(1)
        return sig + (", request_id=None):" if "request_id" not in sig else "):")

    src = re.sub(
        r"(def\s+_get_positions_by_hierarchy\([^)]+)\):",
        add_reqid_param,
        src,
    )

    # ---------- 4) Convert logging.* -> *_id wrappers ----------
    repl_map = {
        r"\blogging\.info\(": "info_id(",
        r"\blogging\.debug\(": "debug_id(",
        r"\blogging\.warning\(": "warning_id(",
        r"\blogging\.error\(": "error_id(",
        r"\blogging\.exception\(": "error_id(",
    }
    for pat, rep in repl_map.items():
        src = re.sub(pat, rep, src)

    # ---------- 5) Drop bare 'import logging' lines if present ----------
    src = re.sub(r"^\s*import\s+logging\s*\r?\n", "", src, flags=re.MULTILINE)

    # ---------- 6) Normalize import header (grouped & sorted) ----------
    # Replace from the first comment line that looks like an import header down to the end
    # of the log_config import tuple (conservative anchor).
    header_pattern = (
        r"(?s)\A\s*#\s*[^\n]*\n"         # initial comment line (e.g., "# Standard library" or any header)
        r".*?"                           # everything up to...
        r"from\s+modules\.configuration\.log_config\s+import\s*\(\s*"
        r".*?error_id\s*,?\s*\)\s*\r?\n" # the closing of the tuple import
    )
    clean_header = (
        "# Standard library\n"
        "from typing import List, Optional\n\n"
        "# SQLAlchemy\n"
        "from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint, select\n"
        "from sqlalchemy.exc import SQLAlchemyError\n"
        "from sqlalchemy.orm import Session, joinedload, relationship\n\n"
        "# Project modules\n"
        "from modules.configuration.base import Base\n"
        "from modules.configuration.config import DatabaseConfig\n"
        "from modules.configuration.log_config import (\n"
        "    logger,\n"
        "    with_request_id,\n"
        "    info_id,\n"
        "    debug_id,\n"
        "    warning_id,\n"
        "    error_id,\n"
        ")\n"
    )
    src = re.sub(header_pattern, clean_header, src, count=1, flags=re.DOTALL)

    # ---------- Write backup and updated file ----------
    backup = target.with_suffix(target.suffix + ".bak")
    copy2(target, backup)
    write_text_utf8(target, src)

    print(f"Updated {target} (backup at {backup}).")
    print("Sanity checks:")
    print(" - Flask imports removed:", "flask" not in src.lower())
    print(" - No g.request_id left:", "g.request_id" not in src)
    print(" - No bare logging.* left:", "logging." not in src)

if __name__ == "__main__":
    main()
