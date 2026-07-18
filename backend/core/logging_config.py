"""Root logging setup.

uvicorn's own logging.config.dictConfig wires handlers onto its own named
loggers (uvicorn, uvicorn.error, uvicorn.access) only — it never touches the
root logger. Without this, a bare logging.getLogger(__name__).info(...)
anywhere else in the app inherits an unconfigured root and goes nowhere
(silently: INFO is below the level of Python's WARNING-only last-resort
handler). disable_existing_loggers=False so uvicorn's own loggers, configured
separately, are left alone.
"""

import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}


def setup_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)
