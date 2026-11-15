"""Logging: timestamped messages to the screen and to a log file, plus step timers."""
import logging
import time
from contextlib import contextmanager
from pathlib import Path

LOGGER_NAME = "cityplaces"


def setup_logging(log_file: str | Path) -> logging.Logger:
    log = logging.getLogger(LOGGER_NAME)
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s  %(levelname)s  %(message)s", "%Y-%m-%d %H:%M:%S")
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    for h in (logging.StreamHandler(), logging.FileHandler(log_file, encoding="utf-8")):
        h.setFormatter(fmt)
        log.addHandler(h)
    log.info("log file: %s", Path(log_file).resolve())
    return log


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


@contextmanager
def timed(step: str):
    """Log start, end and elapsed time of a step; log the error if it fails."""
    log = get_logger()
    log.info("START %s", step)
    t0 = time.time()
    try:
        yield
    except Exception:
        log.exception("FAILED %s after %.1f s", step, time.time() - t0)
        raise
    log.info("DONE  %s in %.1f s", step, time.time() - t0)
