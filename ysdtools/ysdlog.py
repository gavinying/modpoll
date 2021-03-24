"""
.. module:: ysdlog
   :platform: Linux, Windows
   :synopsis: A thin wrapper to logging
.. moduleauthor:: Ying Shaodong <helloysd@gmail.com>
"""
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


def get_logger(name: str):
    """Get a simple logger

    :param name: A name to describe the logger
    :type name: str
    ...
    :return: An instance of logger
    :rtype: logging.Logger
    """
    return logging.getLogger(name)


if __name__ == "__main__":
    logger = get_logger("ysdlog")
    logger.debug("start logging...")
