"""Logging foundation for backend services."""

import logging
import logging.config


def configure_logging(level: str) -> None:
    """Configure process-wide logging with a consistent console format."""
    normalized_level = level.upper()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {
                "handlers": ["console"],
                "level": normalized_level,
            },
        }
    )

