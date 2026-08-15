import logging
import os
import sys
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    # avoid adding duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(
        logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
    )

    # format
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger