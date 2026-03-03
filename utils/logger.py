import logging


def setup_logger(name: str = "CreateTrackLogger", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)

        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger


logger = setup_logger(level=logging.DEBUG)