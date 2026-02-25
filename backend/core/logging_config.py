import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields for structured logging."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        if hasattr(record, "correlation_id"):
            log_record["correlation_id"] = record.correlation_id
        else:
            # Set a default value if correlation_id doesn't exist
            log_record["correlation_id"] = getattr(record, "correlation_id", "")


class CorrelationIdFilter(logging.Filter):
    """Filter to add correlation ID to log records."""

    def __init__(self, correlation_id: Optional[str] = None):
        super().__init__()
        self._correlation_id = correlation_id

    def set_correlation_id(self, correlation_id: Optional[str]) -> None:
        self._correlation_id = correlation_id

    def filter(self, record: logging.LogRecord) -> bool:
        if self._correlation_id:
            record.correlation_id = self._correlation_id
        return True


_correlation_filter = CorrelationIdFilter()


def get_correlation_filter() -> CorrelationIdFilter:
    """Get the global correlation ID filter instance."""
    return _correlation_filter


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """
    Configure centralized logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ('json' or 'text')
        log_file: Optional path to log file for file logging
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if log_format.lower() == "json":
        formatter: logging.Formatter = CustomJsonFormatter(
            "%(message)s",
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(_correlation_filter)
    root_logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(_correlation_filter)
        root_logger.addHandler(file_handler)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging configured",
        extra={
            "level": level,
            "format": log_format,
            "file": log_file or "stdout only",
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
