"""
SbtDeskTran - Application Logger
Writes to app.log in the first writable app data directory.
Usage:
    from logger import log
    log.info("message")
    log.error("error", exc_info=True)
"""
import logging
import sys
from app_paths import data_file

_LOG_FILE = data_file("app.log")

def _setup() -> logging.Logger:
    logger = logging.getLogger("SbtDeskTran")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — rotating, max 2MB, keep 3 backups
    try:
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(
            _LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception as e:
        print(f"[logger] Could not create file handler: {e}", file=sys.stderr)

    # Console handler (only in debug / when console present)
    if sys.stdout and sys.stdout.isatty():
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    return logger


log = _setup()
