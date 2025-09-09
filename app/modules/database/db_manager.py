# app/modules/database/db_manager.py
from contextlib import contextmanager
import logging
from typing import Optional, Tuple, Dict, List

from sqlalchemy import text, inspect as sa_inspect

from app.modules.configuration.database_config import DatabaseConfig, DATABASE_URL

logger = logging.getLogger("shopsync.db")


class ShopSyncDatabase:
    """
    Thin service layer over DatabaseConfig.

    - Accepts echo/enable_wal like older call sites do.
    - Exposes .session_scope(), .create_all(), .drop_all(), .get_engine()
    - Adds .inspect() to return (tables, counts_by_table) for your UI.
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        echo: Optional[bool] = None,
        enable_wal: Optional[bool] = None,
        logger_: Optional[logging.Logger] = None,
        request_id: Optional[str] = None,
    ):
        self._logger = logger_ or logger
        self._request_id = request_id

        # Allow passing a DatabaseConfig instance directly
        if isinstance(db_url, DatabaseConfig):
            self._db = db_url
        else:
            effective_url = db_url or DATABASE_URL
            self._db = DatabaseConfig(
                effective_url,
                echo=echo,
                enable_wal=enable_wal,
                logger_name="shopsync",
            )

        # Use public accessors (DatabaseConfig does not expose .engine attribute)
        self.engine = self._db.get_engine()
        self._SessionLocal = self._db.get_main_sessionmaker()

        if self._logger:
            self._logger.info("[ShopSyncDatabase] Initialized using DatabaseConfig")

    # ---- Session helpers -------------------------------------------------
    @contextmanager
    def session_scope(self):
        # Delegate to DatabaseConfig
        with self._db.session_scope() as s:
            yield s

    def get_engine(self):
        return self._db.get_engine()

    # ---- Schema helpers --------------------------------------------------
    def create_all(self):
        self._db.create_all()

    def drop_all(self):
        self._db.drop_all()

    # ---- Utilities -------------------------------------------------------
    def dispose(self):
        # Dispose underlying engine
        self._db.get_engine().dispose()

    def inspect(self) -> Tuple[List[str], Dict[str, int]]:
        """
        Return (table_names, counts_by_table) for quick UI diagnostics.
        """
        eng = self._db.get_engine()
        insp = sa_inspect(eng)
        tables = insp.get_table_names()
        counts: Dict[str, int] = {}
        # Count rows per table safely
        with eng.connect() as conn:
            for t in tables:
                try:
                    res = conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
                    counts[t] = int(res.scalar() or 0)
                except Exception:
                    # Some virtual tables or views might throw; don’t block the UI
                    counts[t] = -1
        return tables, counts

    # Context manager (optional)
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.dispose()
        return False

    def print_inspect(self):
        # Delegate to DatabaseConfig's implementation
        self._db.print_inspect()
