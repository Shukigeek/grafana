import logging
import os
from logging.handlers import RotatingFileHandler


_CONSOLE_FORMAT = (
    "%(asctime)s.%(msecs)03d  [%(levelname)-8s]  %(name)-30s  %(message)s"
)
_FILE_FORMAT = (
    "%(asctime)s.%(msecs)03d  [%(levelname)-8s]  %(name)-30s  "
    "%(filename)s:%(lineno)d  %(message)s"
)
_DATE_FORMAT = "%H:%M:%S"

def setup_logger(
    name: str = "DroneSimulator",
    level: int = logging.DEBUG,
    log_dir: str = "logs",
    log_file: str = "drone_simulator.log",
    max_bytes: int = 5 * 1024 * 1024,   # 5 MB per file
    backup_count: int = 3,
    console_level: int = logging.INFO,   # keep console quieter than file
    enable_console: bool = True,
    enable_file: bool = True,
) -> logging.Logger:
    """
    Create (or retrieve) a named logger with optional console and file handlers.

    Parameters
    ----------
    name            : Logger name – also used as the root for child loggers
                      (e.g. DroneSimulator.DRONE-001.GPS).
    level           : Master log level for the logger itself.
    log_dir         : Directory where log files are written.
    log_file        : File name inside log_dir.
    max_bytes       : Maximum size of one log file before rotation.
    backup_count    : Number of rotated backup files to keep.
    console_level   : Level applied only to the StreamHandler (lets you keep
                      file=DEBUG while console shows only INFO+).
    enable_console  : Set to False to suppress all console output.
    enable_file     : Set to False to skip writing logs to disk entirely.
    """

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)

    if not enable_console and not enable_file:
        logger.addHandler(logging.NullHandler())
        return logger

    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(
            logging.Formatter(_CONSOLE_FORMAT, datefmt=_DATE_FORMAT)
        )
        logger.addHandler(console_handler)

    if enable_file:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, log_file)
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(_FILE_FORMAT, datefmt=_DATE_FORMAT)
        )
        logger.addHandler(file_handler)

    active = []
    if enable_console:
        active.append(f"console(>={logging.getLevelName(console_level)})")
    if enable_file:
        active.append(f"file={log_path}(>=DEBUG)")

    logger.info(f"Logger '{name}' initialised  handlers=[{', '.join(active)}]")

    return logger


# ── Module-level default logger ────────────────────────────────────────────
#
# Import this anywhere:
#   from logger import get_logger
#   log = get_logger("DroneSimulator.MyModule")

def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the root 'DroneSimulator' hierarchy.
    Call setup_logger() once at startup; after that just use get_logger().
    """
    return logging.getLogger(name)