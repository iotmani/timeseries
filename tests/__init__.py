import logging
from os import getenv

logging.basicConfig(level=int(getenv("DD_TEST_LOG_LEVEL", logging.WARNING)))
