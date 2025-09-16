# app/modules/database/db_manager.py
from contextlib import contextmanager
import logging
from typing import Optional, Tuple, Dict, List

from sqlalchemy import text, inspect as sa_inspect
from sqlalchemy.orm import joinedload

from app.modules.configuration.database_config import DatabaseConfig, DATABASE_URL
from app.modules.configuration.log_config import set_request_id, info_id, error_id, debug_id
from app.modules.database.shopsync_db import DrawerSlot

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

        # Public accessors
        self.engine = self._db.get_engine()

        # Expose a consistent sessionmaker
        self.Session = self._db.get_main_sessionmaker()   # 👈 added
        self._SessionLocal = self.Session                 # keep legacy attr

        if self._logger:
            self._logger.info("[ShopSyncDatabase] Initialized using DatabaseConfig")

    # ---- Session helpers -------------------------------------------------
    @contextmanager
    def session_scope(self):
        session = self.Session()
        request_id = set_request_id()
        try:
            yield session
            try:
                session.flush()
            except Exception as e:
                import traceback
                error_id(f"[session_scope] flush failed: {e!r}", request_id=request_id)
                error_id("".join(traceback.format_exc()), request_id=request_id)
                raise
            session.commit()
        except Exception as e:
            session.rollback()
            error_id(f"[DatabaseConfig] Rolling back due to error: {e!r}", request_id=request_id)
            raise
        finally:
            session.close()

    def get_engine(self):
        return self._db.get_engine()

    # ---- Schema helpers --------------------------------------------------
    def create_all(self):
        self._db.create_all()

    def drop_all(self):
        self._db.drop_all()

    # ---- Utilities -------------------------------------------------------
    def dispose(self):
        self._db.get_engine().dispose()

    def inspect(self) -> Tuple[List[str], Dict[str, int]]:
        """
        Return (table_names, counts_by_table) for quick UI diagnostics.
        """
        eng = self._db.get_engine()
        insp = sa_inspect(eng)
        tables = insp.get_table_names()
        counts: Dict[str, int] = {}
        with eng.connect() as conn:
            for t in tables:
                try:
                    res = conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
                    counts[t] = int(res.scalar() or 0)
                except Exception:
                    counts[t] = -1
        return tables, counts

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.dispose()
        return False

    def print_inspect(self):
        self._db.print_inspect()

