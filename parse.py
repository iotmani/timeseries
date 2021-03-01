import os
import csv
import logging
import typing
from datetime import datetime
from analyze import Processor
from event import HTTPEvent

""" Extract raw log data into an event object """


class Parser:
    def __init__(cls, processor: Processor):
        cls.processor = processor

    """ Parsing implementation here """

    def parse(cls) -> None:
        raise NotImplementedError()


""" Parse HTTP logs and pass them to anlyzer """


class HTTPLogParser(Parser):
    def __init__(cls, processor: Processor, path: str):
        super().__init__(processor)
        logging.basicConfig(level=logging.DEBUG)
        cls.log = logging.getLogger(__name__)
        cls.path = path

    def isSanitised(cls, row: typing.List[str]) -> typing.List[str]:
        if len(row) != 7:
            cls.log.warning("Malformed CSV row: %s", row)
            return False

        # Parse section out of request (row[4])
        row.append(row[4])
        row[7] = row[7].split(" ")
        if len(row[7]) < 2 or len(row[7][1].split("/")) < 2:
            cls.log.warning("Malformed 'section' part of row: %s", row)
            return False
        row[7] = row[7][1].split("/")[1]

        try:
            row.append(datetime.fromtimestamp(int(row[3])))
        except (ValueError, OverflowError, OSError) as e:
            cls.log.warning("Malformed 'date' part of row: %s", row)
            return False

        return True

    def generateEvent(cls, row: typing.List[str]) -> None:
        timestamp = datetime.fromtimestamp(int(row[3]))
        e = HTTPEvent(
            priority=HTTPEvent.Priority.MEDIUM,
            source=row[0],
            rfc931=row[1],
            authuser=row[2],
            time=timestamp,
            request=row[4],
            section=row[7],
            status=row[5],
            size=row[6],
        )
        cls.processor.consume(e)

    def parse(cls) -> None:
        log = cls.log
        log.info("Monitoring HTTP log file %s", cls.path)
        try:
            with open(cls.path, mode="r") as fd:
                logreader = csv.reader(fd)

                # Skip header if exists
                header = next(logreader)
                if len(header) > 0 and header[0] != "remotehost":
                    log.debug("No header")
                    fd.seek(0)
                else:
                    log.debug("Header: %s", header)

                # Parse rows and generate HTTP Log events to send for processing
                [cls.generateEvent(row) for row in logreader if cls.isSanitised(row)]

        except FileNotFoundError as e:
            log.error("HTTP log file doesn't exist: %s", cls.path)
        except csv.Error as ce:
            log.error("HTTP log file not valid CSV: %s", cls.path)
