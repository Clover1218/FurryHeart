import logging
import os
from logging.handlers import TimedRotatingFileHandler


def create_logger(name="heartbot", log_dir="logs"):
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s"
    )

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    fh = TimedRotatingFileHandler(
        filename=f"{log_dir}/app.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8"
    )
    fh.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger