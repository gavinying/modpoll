import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


def get_logger(name: str):
    """
    A thin wrapper to logging
    Get a simple logger to output to stdout
    :param name:
    :return:logging.Logger
    """
    return logging.getLogger(name)


if __name__ == "__main__":
    logger = get_logger("ysdlog")
    logger.debug("start logging...")
