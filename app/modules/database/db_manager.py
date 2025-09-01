# app/modules/database/db_manager.py
from __future__ import annotations

import os
import logging
from contextlib import contextmanager
from typing import Iterator, Optional, Dict, Any, Tuple

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

# --- Your project's Base (DeclarativeBase) ---
# If you ever move Base, only this import changes.
from app.modules.configuration.base import Base  # Declarative Base

# Try to use your shared logger if present; fall back to stdlib logging
try:
    # Optional: your central logger (adjust path if different)
    from app.modules.configuration.log_config import get_logger  # type: ignore

    logger = get_logger("ShopSyncDB")
except Exception:
    logger = logging.getLogger("ShopSyncDB")
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(h)
        logger.setLevel(logging.INFO)


class ShopSyncDatabase:
    """
    Centralized database manager for SQLite.

    Default location:
      app/modules/database/shopsync.db

    Key features:
      - Single place to create/get engine and sessions
      - Foreign keys ON for SQLite
      - Optional WAL + synchronous NORMAL for better dev UX
      - Helpers: create_all, drop_all, inspect, execute
    """

    def __init__(
        self,
        db_dir: Optional[str] = None,
        db_filename: str = "shopsync.db",
        echo: bool = False,
        enable_wal: bool = False,
    ) -> None:
        """
        Args:
            db_dir: directory for the SQLite file; defaults to app/modules/database/
            db_filename: SQLite file name
            echo: SQLAlchemy echo (debug SQL)
            enable_wal: enable WAL + synchronous NORMAL on connect (SQLite only)
        """
        # Resolve default DB directory inside the project
        if db_dir is None:
            # Project root assumed to be one level above "app"
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            db_dir = os.path.join(project_root, "modules", "database")

        self.db_path = os.path.join(db_dir, db_filename)
        self.db_url = f"sqlite:///{self.db_path}"
        self.echo = echo
        self.enable_wal = enable_wal

        os.makedirs(db_dir, exist_ok=True)

        self._engine: Optional[Engine] = None
        self._SessionLocal: Optional[sessionmaker] = None

        logger.info(f"DB path set to: {self.db_path}")

    # ---------------------------
    # Engine / Session lifecycle
    # ---------------------------
    def _build_engine(self) -> Engine:
        engine = create_engine(self.db_url, echo=self.echo, future=True)

        # Always enforce SQLite foreign keys
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):
            try:
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys = ON")
                if self.enable_wal:
                    # WAL helps with concurrent readers; harmless for single-user dev
                    cur.execute("PRAGMA journal_mode=WAL")
                    cur.execute("PRAGMA synchronous=NORMAL")
                cur.close()
            except Exception:  # pragma: no cover
                # Don't crash engine creation if pragmas fail; just log
                logger.exception("Failed to apply SQLite PRAGMAs")

        return engine

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = self._build_engine()
        return self._engine

    @property
    def SessionLocal(self) -> sessionmaker:
        if self._SessionLocal is None:
            self._SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        return self._SessionLocal

    def get_session(self) -> Session:
        """Plain session (remember to close/commit/rollback yourself)."""
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """
        Preferred way: transactional scope that commits on success,
        rolls back on error, and always closes.
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Transaction rolled back due to error.")
            raise
        finally:
            session.close()

    # ---------------------------
    # Schema helpers
    # ---------------------------
    def create_all(self) -> None:
        """
        Create all tables registered on Base.metadata.
        Safe to run multiple times.
        """
        logger.info("Creating all tables from Base.metadata…")
        Base.metadata.create_all(self.engine)
        logger.info("Done creating tables.")

    def drop_all(self) -> None:
        """
        Drop ALL tables (destructive) — dev only!
        """
        logger.warning("Dropping ALL tables…")
        Base.metadata.drop_all(self.engine)
        logger.info("All tables dropped.")

    def inspect(self) -> Tuple[list[str], Dict[str, Optional[int]]]:
        """
        Returns:
          (tables, row_counts)
          tables: list of table names
          row_counts: mapping table -> count (None if count failed)
        """
        from sqlalchemy import inspect as sa_inspect

        insp = sa_inspect(self.engine)
        tables = sorted(insp.get_table_names())
        counts: Dict[str, Optional[int]] = {}

        with self.engine.connect() as conn:
            for t in tables:
                try:
                    counts[t] = conn.execute(text(f"SELECT COUNT(1) FROM {t}")).scalar_one()
                except Exception:
                    counts[t] = None
        return tables, counts

    # ---------------------------
    # Utility helpers
    # ---------------------------
    def connect(self) -> Connection:
        """Context-managed raw connection: `with db.connect() as conn:`"""
        return self.engine.connect()

    def execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Execute arbitrary SQL (use sparingly)."""
        try:
            with self.engine.begin() as conn:
                conn.execute(text(sql), params or {})
        except SQLAlchemyError:
            logger.exception("SQL execution failed.")
            raise

    # ---------------------------
    # Convenience CLI-ish methods
    # ---------------------------
    def print_inspect(self) -> None:
        tables, counts = self.inspect()
        if not tables:
            logger.info("No tables found.")
            return
        logger.info("Tables present:")
        for t in tables:
            logger.info(f"  - {t:30s}  rows={counts.get(t)}")
