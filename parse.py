import os
import logging
from analyze import Processor
from event import Event, HTTPEvent
from datetime import datetime

""" Extract raw log data into an event object """


class Parser:
    def __init__(cls, processor: Processor):
        cls.processor = processor

    """ Parsing implementation here """

    def parse(cls) -> None:
        raise NotImplementedError()


""" Parse HTTP logs and pass them to anlyzer """


class HTTPLogParser(Parser):
    def __init__(cls, processor: Processor, path: str = None):
        super().__init__(processor)
        cls.path = path or os.getenv("DD_HTTP_LOG_FILE", "sample_csv.txt")
        logging.basicConfig(level=logging.DEBUG)
        cls.log = logging.getLogger(__name__)

    def parse(cls) -> None:
        e = HTTPEvent(source="192.168.0.1", time=datetime.now())
        cls.processor.consume([e] * 3)
        cls.log.debug("Monitoring HTTP log file %s", cls.path)
