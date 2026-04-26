"""Shared logging helpers for the agentskill CLI."""

import logging
import sys

LOGGER_NAME = "agentskill"
LOG_FORMAT = "%(levelname)s %(name)s: %(message)s"
HANDLER_NAME = "agentskill.stderr"


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def configure_logging() -> logging.Logger:
    logger = get_logger()
    formatter = logging.Formatter(LOG_FORMAT)

    existing = [entry for entry in logger.handlers if entry.get_name() == HANDLER_NAME]

    for handler in existing:
        logger.removeHandler(handler)
        handler.close()

    handler = logging.StreamHandler(sys.stderr)
    handler.set_name(HANDLER_NAME)
    logger.addHandler(handler)

    handler.setFormatter(formatter)
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    return logger
