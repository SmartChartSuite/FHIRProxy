"""Application logging configuration."""

from __future__ import annotations

import logging
import os
import sys

from loguru import logger

_LOG_FORMAT = "<level>{time:MM/DD/YYYY hh:mm:ss A} | {level:<8} | {name}:{function}:{line} - {message}</level>"


class InterceptHandler(logging.Handler):
    """Route standard-library log records through Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        logger.opt(exception=record.exc_info, depth=6).log(level, record.getMessage())


def configure_logging(level: str) -> None:
    """Configure application and standard-library logging."""
    normalized_level = level.upper()
    try:
        logger.level(normalized_level)
    except ValueError:
        normalized_level = "INFO"

    logger.remove()
    logger.add(
        sys.stderr,
        level=normalized_level,
        format=_LOG_FORMAT,
        colorize=True,
        backtrace=False,
        diagnose=False,
    )

    intercept_handler = InterceptHandler()
    logging.basicConfig(handlers=[intercept_handler], level=0, force=True)
    for name in ("fastapi", "fhir.resources", "fhirsearchhelper", "httpcore", "httpx", "hypercorn", "uvicorn", "uvicorn.access"):
        module_logger = logging.getLogger(name)
        module_logger.handlers = [intercept_handler]
        module_logger.propagate = False

    logging.getLogger("fhir.resources").setLevel(logging.ERROR)
    for name in ("fhirsearchhelper", "httpcore", "httpx"):
        logging.getLogger(name).setLevel(logging.WARNING)


configure_logging(os.environ.get("LOG_LEVEL", "INFO"))
