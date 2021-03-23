import ysdtools


def test_version():
    assert ysdtools.__version__ == "0.1.0"


def test_ysdlog():
    logger = ysdtools.ysdlog.get_logger("test_ysdtools")
    logger.debug("logging from test_ysdtools")
    assert True
