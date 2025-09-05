# modules/configuration/log_config.py
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
import gzip
import shutil
from datetime import datetime, timedelta
import uuid
import time
import threading
import functools
from typing import Optional
from pathlib import Path

# Determine the root directory based on whether the code is frozen (e.g., PyInstaller .exe)
if getattr(sys, 'frozen', False):  # Running as an executable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the current directory to the Python module search path for flexibility
sys.path.append(BASE_DIR)

# Configure logging - ShopSync specific logger
logger = logging.getLogger('shopsync')
logger.setLevel(logging.DEBUG)

# Ensure the log directory exists
log_directory = os.path.join(BASE_DIR, 'logs')
log_backup_directory = os.path.join(BASE_DIR, 'log_backup')
os.makedirs(log_directory, exist_ok=True)
os.makedirs(log_backup_directory, exist_ok=True)

# Ensure the training log directory exists
# --- Training logs mirror app log structure ---
TRAINING_LOG_DIR = os.path.join(log_directory, 'training')
TRAINING_LOG_BACKUP_DIR = os.path.join(log_backup_directory, 'training')
os.makedirs(TRAINING_LOG_DIR, exist_ok=True)
os.makedirs(TRAINING_LOG_BACKUP_DIR, exist_ok=True)

# Create a RotatingFileHandler
file_handler = RotatingFileHandler(
    os.path.join(log_directory, 'app.log'),
    maxBytes=5 * 1024 * 1024,  # 5 MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)

# Create a StreamHandler (console)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# Create a formatter and set it for both handlers
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Force UTF-8 encoding for console output (Windows compatibility)
if sys.platform.startswith('win'):
    # Try to set console to UTF-8 on Windows
    try:
        os.system('chcp 65001 >nul')  # Set console to UTF-8
    except:
        pass

# Add both handlers to the logger if they aren't already added
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# Optionally, prevent log messages from being propagated to the root logger
logger.propagate = False

# UUID-BASED REQUEST/SESSION TRACKING
# ==================================

# Thread-local storage for request/session IDs
_local = threading.local()


def with_request_id(func):
    """
    Decorator that adds request/session ID tracking to a function.
    Creates a new ID if one doesn't exist.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        request_id = get_request_id()
        start_time = time.time()

        debug_id(f"Starting {func.__name__}", request_id)
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            debug_id(f"Completed {func.__name__} in {end_time - start_time:.3f}s", request_id)
            return result
        except Exception as e:
            end_time = time.time()
            error_id(f"Error in {func.__name__} after {end_time - start_time:.3f}s: {e}", request_id)
            raise

    return wrapper


def get_request_id():
    """
    Get the current request/session ID from thread-local storage.
    If none exists, generate a new one.
    """
    # Try thread-local storage
    if hasattr(_local, 'request_id'):
        return _local.request_id

    # If no request ID exists, generate a new one
    request_id = str(uuid.uuid4())[:8]
    _local.request_id = request_id
    return request_id


def set_request_id(request_id=None):
    """
    Set a request/session ID in thread-local storage.
    If no request_id is provided, generate a new one.
    Returns the request ID that was set.
    """
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]

    _local.request_id = request_id
    return request_id


def clear_request_id():
    """Clear the request/session ID from thread-local storage."""
    if hasattr(_local, 'request_id'):
        delattr(_local, 'request_id')


def log_with_id(level, message, request_id=None, *args, **kwargs):
    """Log message with request/session ID, with bulletproof Unicode handling."""
    try:
        # Use provided request_id or get current one
        if request_id is None:
            request_id = get_request_id()

        if request_id:
            final = f"[REQ-{request_id}] {message}"
        else:
            final = message

        # BULLETPROOF Unicode handling - convert everything to ASCII-safe representation
        try:
            # First, try to encode to the console's encoding to see if it works
            console_encoding = sys.stdout.encoding or 'cp1252'
            final.encode(console_encoding)
            # If we get here, the string is safe to log
        except (UnicodeEncodeError, AttributeError):
            # String contains characters that can't be encoded - make it safe
            import unicodedata

            # Method 1: Remove combining characters (like Ìˆ)
            normalized = unicodedata.normalize('NFD', final)
            without_combining = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

            # Method 2: Replace remaining problematic characters
            safe_chars = []
            for char in without_combining:
                try:
                    char.encode('cp1252')  # Test if char works in Windows console
                    safe_chars.append(char)
                except UnicodeEncodeError:
                    # Replace with safe equivalent or description
                    char_code = ord(char)
                    if char_code < 256:
                        safe_chars.append(char)  # Should be safe
                    else:
                        # Replace with Unicode code point
                        safe_chars.append(f"U+{char_code:04X}")

            final = ''.join(safe_chars)

        # Try to log the safe message
        if level == logging.DEBUG:
            logger.debug(final, *args, **kwargs)
        elif level == logging.INFO:
            logger.info(final, *args, **kwargs)
        elif level == logging.WARNING:
            logger.warning(final, *args, **kwargs)
        elif level == logging.ERROR:
            logger.error(final, *args, **kwargs)
        elif level == logging.CRITICAL:
            logger.critical(final, *args, **kwargs)

    except Exception as e:
        # Ultimate fallback - create the simplest possible log message
        try:
            simple_msg = f"[REQ-{request_id or 'unknown'}] LOG_ENCODING_ERROR: {str(e)[:100]}"
            # Remove any remaining problematic characters
            ascii_only = simple_msg.encode('ascii', 'replace').decode('ascii')
            logger.error(ascii_only)
        except:
            # Last resort - print to console
            print(f"CRITICAL LOGGING FAILURE - REQUEST: {request_id or 'unknown'}")


# Convenience functions that match the logger interface
def debug_id(message, request_id=None, *args, **kwargs):
    log_with_id(logging.DEBUG, message, request_id, *args, **kwargs)


def info_id(message, request_id=None, *args, **kwargs):
    log_with_id(logging.INFO, message, request_id, *args, **kwargs)


def warning_id(message, request_id=None, *args, **kwargs):
    log_with_id(logging.WARNING, message, request_id, *args, **kwargs)


def error_id(message, request_id=None, *args, **kwargs):
    log_with_id(logging.ERROR, message, request_id, *args, **kwargs)


def critical_id(message, request_id=None, *args, **kwargs):
    log_with_id(logging.CRITICAL, message, request_id, *args, **kwargs)


# Helper for timing operations
def log_timed_operation(operation_name, request_id=None):
    """Context manager for timing and logging operations."""

    class TimedOperationContext:
        def __init__(self, operation_name, request_id):
            self.operation_name = operation_name
            self.request_id = request_id if request_id else get_request_id()

        def __enter__(self):
            self.start_time = time.time()
            debug_id(f"Starting operation: {self.operation_name}", self.request_id)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            if exc_type:
                error_id(f"Operation {self.operation_name} failed after {duration:.3f}s: {str(exc_val)}",
                         self.request_id)
            else:
                debug_id(f"Operation {self.operation_name} completed in {duration:.3f}s",
                         self.request_id)

    return TimedOperationContext(operation_name, request_id)


# LOG ROTATION AND BACKUP
# =======================

def compress_and_backup_logs(log_directory, backup_directory):
    """
    Consolidate and compress log files older than 14 days into biweekly backup files.

    This function groups log files (that are not already compressed) by a biweekly period.
    For each biweekly group, the log files are concatenated into a single gzip file, and
    then the original files are removed.
    """
    now = datetime.now()
    biweekly_logs = {}

    # Group log files older than 14 days by their biweekly period.
    for file_name in os.listdir(log_directory):
        file_path = os.path.join(log_directory, file_name)
        # Skip directories and files that are already compressed.
        if os.path.isdir(file_path) or file_name.endswith('.gz'):
            continue

        file_modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        if now - file_modified_time > timedelta(days=14):
            # Calculate the biweekly period based on the day of the year.
            year = file_modified_time.year
            day_of_year = file_modified_time.timetuple().tm_yday
            biweek = (day_of_year - 1) // 14 + 1  # Determines the biweekly period number
            biweek_key = f"{year}-BW{biweek:02d}"
            biweekly_logs.setdefault(biweek_key, []).append(file_path)
            logger.debug(f"Grouping file {file_path} under biweekly period {biweek_key}")

    # For each biweekly group, consolidate logs into a single compressed backup file.
    for biweek_key, files in biweekly_logs.items():
        backup_file_path = os.path.join(backup_directory, f"backup_{biweek_key}.gz")
        logger.info(f"Creating biweekly backup: {backup_file_path} with {len(files)} file(s)")
        with gzip.open(backup_file_path, 'wb') as f_out:
            for file_path in files:
                with open(file_path, 'rb') as f_in:
                    shutil.copyfileobj(f_in, f_out)
                os.remove(file_path)
                logger.info(f"Compressed and removed: {file_path}")


def delete_old_backups(backup_directory, retention_weeks=2):
    """
    Delete backup files older than the specified retention period (in weeks).

    :param backup_directory: Path to the backup directory.
    :param retention_weeks: Number of weeks to retain backups (default is 2).
    """
    now = datetime.now()
    for file_name in os.listdir(backup_directory):
        file_path = os.path.join(backup_directory, file_name)
        # Skip directories
        if os.path.isdir(file_path):
            continue
        # Process only compressed backup files.
        if file_name.endswith('.gz'):
            file_modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if now - file_modified_time > timedelta(weeks=retention_weeks):
                os.remove(file_path)
                logger.info(f"Deleted old backup: {file_path}")


def initial_log_cleanup():
    """
    Perform initial cleanup by consolidating log files into biweekly backups
    and deleting backups older than 2 weeks.
    """
    logger.info("Starting initial log cleanup...")
    compress_and_backup_logs(log_directory, log_backup_directory)
    delete_old_backups(log_backup_directory, retention_weeks=2)
    logger.info("Initial log cleanup completed.")


def maintain_training_logs(retention_weeks: int = 2):
    """
    Mirror the app log maintenance for training logs:
      - consolidate+compress logs older than 14 days into biweekly .gz backups
      - delete backups older than `retention_weeks`
    """
    try:
        logger.info("Starting training log cleanup...")
        compress_and_backup_logs(TRAINING_LOG_DIR, TRAINING_LOG_BACKUP_DIR)
        delete_old_backups(TRAINING_LOG_BACKUP_DIR, retention_weeks=retention_weeks)
        logger.info("Training log cleanup complete.")
    except Exception as e:
        logger.exception(f"Training log maintenance failed: {e}")


# TRAINING LOG MANAGER
# ===================

class TrainingLogManager:
    """
    Dedicated training logger:
    - Non-propagating (won't pollute app logs)
    - Writes to <run_dir>/training.log when run_dir is given, else BASE_DIR/logs/training/training.log
    - Optional console mirror
    - Context-manager closes handlers cleanly
    - make_trainer_callback(): HF TrainerCallback to send metrics to this log
    """

    def __init__(
            self,
            run_dir: Optional[os.PathLike] = None,
            run_name: Optional[str] = None,
            to_console: bool = False,
            level: int = logging.INFO,
            rotate_mb: int = 10,
            backups: int = 5,
    ):
        self.run_dir = Path(run_dir) if run_dir else None
        self.run_name = run_name or (self.run_dir.name if self.run_dir else "global")
        self.logger_name = f"shopsync_train.{self.run_name}"
        self.level = level
        self.to_console = to_console
        self.rotate_mb = rotate_mb
        self.backups = backups

        self._logger = logging.getLogger(self.logger_name)
        self._logger.setLevel(level)
        self._logger.propagate = False
        self._adapter = None

        self._attach_handlers()

    @property
    def logger(self) -> logging.LoggerAdapter:
        return self._adapter

    def _attach_handlers(self):
        # Ensure global training dirs exist
        os.makedirs(TRAINING_LOG_DIR, exist_ok=True)
        os.makedirs(TRAINING_LOG_BACKUP_DIR, exist_ok=True)

        # Choose target file
        if self.run_dir:
            # Per-run file next to model artifacts
            log_path = self.run_dir / "training.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            log_path = Path(TRAINING_LOG_DIR) / "training.log"

        # Avoid duplicate handlers
        def _same_file(h):
            return isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == os.path.abspath(
                str(log_path))

        if not any(_same_file(h) for h in self._logger.handlers):
            fh = RotatingFileHandler(str(log_path), maxBytes=self.rotate_mb * 1024 * 1024,
                                     backupCount=self.backups, encoding="utf-8")
            fh.setLevel(self.level)
            fh.setFormatter(logging.Formatter(
                "%(asctime)s - shopsync_train - [%(run)s] %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
            ))
            self._logger.addHandler(fh)

        if self.to_console and not any(isinstance(h, logging.StreamHandler) for h in self._logger.handlers):
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(self.level)
            ch.setFormatter(logging.Formatter(
                "%(asctime)s - shopsync_train - [%(run)s] %(levelname)s - %(message)s"
            ))
            self._logger.addHandler(ch)

        # Adapter injects [run] field so formatter can include it
        self._adapter = logging.LoggerAdapter(self._logger, extra={"run": self.run_name})

    def make_trainer_callback(self):
        """Return a HF TrainerCallback that mirrors logs/eval metrics into this training logger."""
        try:
            from transformers import TrainerCallback
        except ImportError:
            # Return a no-op class if transformers is not available
            class _NoopCallback:
                pass

            return _NoopCallback()

        adapter = self._adapter

        class _MetricsToLogger(TrainerCallback):
            def on_log(self, args, state, control, logs=None, **kwargs):
                if logs:
                    adapter.info(f"HF_LOG: {logs}")

            def on_evaluate(self, args, state, control, metrics=None, **kwargs):
                if metrics:
                    adapter.info(f"EVAL: {metrics}")

            def on_train_end(self, args, state, control, **kwargs):
                adapter.info("Training finished.")

        return _MetricsToLogger()

    def close(self):
        """Flush/close handlers; useful for repeated runs / tests."""
        for h in list(self._logger.handlers):
            try:
                h.flush()
                h.close()
            except Exception:
                pass
            self._logger.removeHandler(h)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()