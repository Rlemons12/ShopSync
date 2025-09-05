#!/usr/bin/env python3
"""
DatabaseConfig: central place to configure SQLAlchemy engine/session for the project.

- Supports SQLite and PostgreSQL via a single DB URL (env or .env or argument).
- Exposes:
    - get_engine()
    - get_main_sessionmaker()
    - get_main_session()          # one-off session
    - session_scope()             # contextmanager
    - create_all() / drop_all() / print_inspect()

- SQLite quality-of-life:
    - WAL mode (optional)
    - PRAGMA foreign_keys=ON
    - Echo flag for SQL

Typical DB URLs:
    SQLite (file):     sqlite:///path/to/shopsync.db
    SQLite (memory):   sqlite://
    PostgreSQL:        postgresql+psycopg2://user:pass@host:5432/dbname
"""

from __future__ import annotations
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Callable

# --- Optional dotenv load (safe no-op if not installed) ---
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

from sqlalchemy import create_engine, event, text, inspect as sa_inspect
from sqlalchemy.orm import sessionmaker, Session

# ----------------------------------------------------------------------
# Import your Base (models) — try a couple of common paths
# ----------------------------------------------------------------------
Base = None
_models_import_errors = []

def _import_models():
    global Base
    candidates = [
        # Adjust these to your project’s layout if needed
        "app.modules.database.shopsync_db",
        "modules.emtacdb.shopsync_db",
        "shopsync_db",  # local file next to the running script
    ]
    for modname in candidates:
        try:
            mod = __import__(modname, fromlist=["Base"])
            Base = getattr(mod, "Base", None)
            if Base is not None:
                return
        except Exception as e:
            _models_import_errors.append(f"{modname}: {e!r}")

    raise ImportError(
        "Could not import Base from shopsync_db. Tried:\n  - " +
        "\n  - ".join(_models_import_errors)
    )

_import_models()

# ----------------------------------------------------------------------
# Optional logging wrappers (fallback to basic logging if missing)
# ----------------------------------------------------------------------
try:
    from modules.configuration.log_config import info_id, debug_id, error_id, set_request_id, get_request_id
except Exception:
    try:
        from app.modules.configuration.log_config import info_id, debug_id, error_id, set_request_id, get_request_id
    except Exception:
        import logging
        _logger = logging.getLogger("dbconfig")
        if not _logger.handlers:
            _logger.addHandler(logging.StreamHandler(sys.stdout))
        _logger.setLevel(logging.INFO)

        _REQ_ID = None
        def set_request_id(req_id: Optional[str] = None):
            nonlocal_vars = globals()
            rid = req_id or "REQ-DBCONF"
            nonlocal_vars["_REQ_ID"] = rid
            return rid
        def get_request_id() -> str:
            return globals().get("_REQ_ID") or "REQ-DBCONF"
        def info_id(msg: str, request_id: Optional[str] = None): _logger.info(f"[{get_request_id()}] {msg}")
        def debug_id(msg: str, request_id: Optional[str] = None): _logger.debug(f"[{get_request_id()}] {msg}")
        def error_id(msg: str, request_id: Optional[str] = None): _logger.error(f"[{get_request_id()}] {msg}")

# ----------------------------------------------------------------------
# Config dataclass
# ----------------------------------------------------------------------
@dataclass
class _Settings:
    db_url: str
    echo: bool = False
    enable_wal: bool = False

def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "t", "yes", "y", "on"}

def _default_db_url() -> str:
    # Prefer explicit env, else local sqlite file
    return os.getenv("DB_URL", "sqlite:///shopsync.db")

# ----------------------------------------------------------------------
# DatabaseConfig
# ----------------------------------------------------------------------
class DatabaseConfig:
    """
    Central entry point for creating engine/session and managing schema.

    Priority of settings:
      1) Explicit arguments passed to __init__
      2) Environment variables:
           DB_URL, DB_ECHO, DB_ENABLE_WAL
      3) Safe defaults: sqlite:///shopsync.db, echo=False, wal=False
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        echo: Optional[bool] = None,
        enable_wal: Optional[bool] = None,
    ):
        self.request_id = set_request_id()  # ensure logging correlates
        self.settings = _Settings(
            db_url=db_url or _default_db_url(),
            echo=echo if echo is not None else _env_bool("DB_ECHO", False),
            enable_wal=enable_wal if enable_wal is not None else _env_bool("DB_ENABLE_WAL", False),
        )
        info_id(f"[DatabaseConfig] DB={self.settings.db_url} echo={self.settings.echo} wal={self.settings.enable_wal}",
                self.request_id)

        # Create engine and session factory
        self._engine = create_engine(self.settings.db_url, echo=self.settings.echo, future=True)
        self._SessionFactory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)

        # If SQLite ⇒ apply PRAGMAs
        if self._is_sqlite():
            self._install_sqlite_pragmas()

        # You can add PostgreSQL-specific tuning here if desired.

    # ------------- Public API ----------------
    def get_engine(self):
        return self._engine

    def get_main_sessionmaker(self):
        """Return the project's canonical sessionmaker factory."""
        return self._SessionFactory

    def get_main_session(self) -> Session:
        """Return a fresh Session (use session_scope in most cases)."""
        return self._SessionFactory()

    @contextmanager
    def session_scope(self):
        """Transactional scope around a series of operations."""
        session = self._SessionFactory()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            error_id(f"[DatabaseConfig] Rolling back due to error: {exc!r}", self.request_id)
            raise
        finally:
            session.close()

    # ----- Schema helpers -----
    def create_all(self):
        """Create all tables from models' Base.metadata."""
        Base.metadata.create_all(self._engine)
        info_id("[DatabaseConfig] create_all complete", self.request_id)

    def drop_all(self):
        """Drop all tables (DANGEROUS; typically for dev/test)."""
        Base.metadata.drop_all(self._engine)
        info_id("[DatabaseConfig] drop_all complete", self.request_id)

    def print_inspect(self):
        """Print a compact schema inventory."""
        insp = sa_inspect(self._engine)
        for tbl in insp.get_table_names():
            cols = [c["name"] for c in insp.get_columns(tbl)]
            info_id(f"[inspect] {tbl}: {', '.join(cols)}", self.request_id)

    # ------------- Internals -----------------
    def _is_sqlite(self) -> bool:
        return self.settings.db_url.startswith("sqlite")

    def _install_sqlite_pragmas(self):
        """Enable WAL and foreign_keys for SQLite connections."""
        enable_wal = self.settings.enable_wal

        @event.listens_for(self._engine, "connect")
        def _set_sqlite_pragmas(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            try:
                # Foreign keys ON
                cursor.execute("PRAGMA foreign_keys=ON;")
                # WAL if requested and not memory DB
                if enable_wal and not self.settings.db_url.endswith(":memory:"):
                    cursor.execute("PRAGMA journal_mode=WAL;")
            finally:
                cursor.close()

# ----------------------------------------------------------------------
# Optional: a thin "DB Manager" wrapper (used by older scripts)
# ----------------------------------------------------------------------
class ShopSyncDatabase:
    """
    Backward-compatible helper class mirroring your initializer’s expectations:
      - create_all(), drop_all(), print_inspect()
      - exposes .session_scope() for transactional work

    This lets scripts that import ShopSyncDatabase keep working, while internally
    leveraging DatabaseConfig.
    """
    def __init__(self, db_url: Optional[str] = None, echo: bool = False, enable_wal: bool = False):
        self.cfg = DatabaseConfig(db_url=db_url, echo=echo, enable_wal=enable_wal)

    def create_all(self): self.cfg.create_all()
    def drop_all(self): self.cfg.drop_all()
    def print_inspect(self): self.cfg.print_inspect()
    def get_engine(self): return self.cfg.get_engine()
    def get_main_sessionmaker(self): return self.cfg.get_main_sessionmaker()
    def get_main_session(self): return self.cfg.get_main_session()
    def session_scope(self): return self.cfg.session_scope()
