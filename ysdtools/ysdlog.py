import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


def get_logger(name: str):
    """
    Get a simple logger

    Args:
        name(str): A name for logger

    Returns:
        A default logger

    """
    return logging.getLogger(name)


if __name__ == "__main__":
    logger = get_logger("ysdlog")
    logger.debug("start logging...")
