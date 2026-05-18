import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_DIR = os.environ.get("LOG_DIR", "./logs")
LOG_FILE = os.path.join(LOG_DIR, "worker.log")
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_logger: logging.Logger | None = None


class _SysStdoutProxy:
    """Proxy that always writes to the current sys.stdout.

    Using sys.stdout directly in StreamHandler captures the reference at
    handler-creation time, which breaks pytest capsys (capsys replaces
    sys.stdout per-test, but the handler still holds the original stream).
    This proxy defers the lookup so capsys interception works correctly.
    """

    def write(self, msg: str) -> int:
        return sys.stdout.write(msg)

    def flush(self) -> None:
        sys.stdout.flush()


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(_SysStdoutProxy())
    stream_handler.setFormatter(formatter)

    logger = logging.getLogger("worker")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    _logger = logger
    return _logger


def log(scope: str, message: str) -> None:
    _get_logger().info("[%s] %s", scope, message)
