"""Logging configuration for RU-WiFi."""

from __future__ import annotations

from pathlib import Path
import logging


def setup_logging(log_file: Path | None) -> logging.Logger:
    """Create a logger configured for console or file output."""

    logger = logging.getLogger("ru_wifi")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    handler: logging.Handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
