import logging

FORMAT_SIMPLE = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"

logging.basicConfig(
    level=logging.DEBUG,
    format=FORMAT_SIMPLE,
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
