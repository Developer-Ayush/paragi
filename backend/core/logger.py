"""core/logger.py — Structured logging for the Paragi cognitive runtime."""
from __future__ import annotations

import logging
import sys
from typing import Optional


def get_logger(name: str, *, level: Optional[int] = None) -> logging.Logger:
    """
    Return a configured logger for the given module name.

    Usage:
        from core.logger import get_logger
        log = get_logger(__name__)
        log.info("Graph updated", extra={"nodes": 5})
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.propagate = False

    if level is not None:
        logger.setLevel(level)
    elif logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)

    return logger


# Module-level root logger for quick imports
root_logger = get_logger("paragi")
