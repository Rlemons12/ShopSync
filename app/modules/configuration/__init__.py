"""
Configuration module for the application.

This module provides:
- Base SQLAlchemy declarative base
- Comprehensive logging system with request ID tracking
- Training-specific logging capabilities
- Log rotation and cleanup utilities
"""

# Import base configuration
from .base import Base, BASE_DIR

# Import main logger and logging functions
from .log_config import (
    logger,
    # Request ID functions
    get_request_id,
    set_request_id,
    clear_request_id,
    with_request_id,

    # Logging functions with request ID support
    debug_id,
    info_id,
    warning_id,
    error_id,
    critical_id,
    log_with_id,

    # Utility functions
    log_timed_operation,

    # Log maintenance functions
    initial_log_cleanup,
    maintain_training_logs,
    compress_and_backup_logs,
    delete_old_backups,

    # Training logger
    TrainingLogManager,

    # Directory constants
    TRAINING_LOG_DIR,
    TRAINING_LOG_BACKUP_DIR,
)

# Make commonly used items available at package level
__all__ = [
    # Base components
    'Base',
    'BASE_DIR',

    # Main logger
    'logger',

    # Request ID management
    'get_request_id',
    'set_request_id',
    'clear_request_id',
    'with_request_id',

    # Logging with request ID
    'debug_id',
    'info_id',
    'warning_id',
    'error_id',
    'critical_id',
    'log_with_id',

    # Utilities
    'log_timed_operation',

    # Log maintenance
    'initial_log_cleanup',
    'maintain_training_logs',
    'compress_and_backup_logs',
    'delete_old_backups',

    # Training logging
    'TrainingLogManager',

    # Constants
    'TRAINING_LOG_DIR',
    'TRAINING_LOG_BACKUP_DIR',
]

# Package metadata
__version__ = '1.0.0'
__author__ = 'Your Name'
__description__ = 'Configuration and logging module for the application'
