import os
import csv
import typing
import logging
from event import WebEvent
from analyze import Processor
from datetime import datetime


class Parser:
    """ Extract raw log data into an event object """

    def __init__(cls, processor: Processor):
        cls.processor = processor

    def parse(cls) -> None:
        """ Parsing implementation here """
        raise NotImplementedError()


class HTTPLogParser(Parser):
    """ Parses HTTP logs and generates WebEvent type of events """

    def __init__(cls, processor: Processor, path: str):
        super().__init__(processor)
        cls._log = logging.getLogger(__name__)
        cls._path = path

    def parse(cls) -> None:
        """ Parse raw data from log file and generate log event object """

        log = cls._log
        log.info(f"Monitoring HTTP log file {cls._path}")
        try:
            with open(cls._path, mode="r") as fd:
                logreader = csv.reader(fd)

                # Skip header if exists
                header = next(logreader)
                if len(header) > 0 and header[0] != "remotehost":
                    log.debug("No header")
                    fd.seek(0)
                else:
                    log.debug(f"Header: {header}")

                # Parse rows in best-effort mode (skip any bad lines)
                # and generate WebEvents to send for processing
                for row in logreader:
                    if cls._isSanitised(row):
                        cls._generateEvent(row)

        except FileNotFoundError as e:
            log.error(f"HTTP log file doesn't exist: {cls._path}")
        except csv.Error as ce:
            log.error(f"HTTP log file not valid CSV: {cls._path}")

    def _isSanitised(cls, row: typing.List[str]) -> bool:
        """ Sanitise row columns data types and parse data within as needed. """
        if len(row) != 7:
            cls._log.warning(f"Malformed CSV row: {row}")
            return False

        # Parse section out of request, i.e. row[4]
        section = row[4].split(" ")
        if len(section) < 2 or len(section[1].split("/")) < 2:
            cls._log.warning(f"Malformed 'section' part of row: {row}")
            return False
        row.append("/" + section[1].split("/")[1])

        try:
            datetime.fromtimestamp(int(row[3]))
        except (ValueError, OverflowError, OSError) as e:
            cls._log.warning(f"Malformed 'date' part of row: {row}")
            return False

        return True

    def _generateEvent(cls, row: typing.List[str]) -> None:
        """ Build event object from pre-sanitised data and send for processing """

        timestamp = datetime.fromtimestamp(int(row[3]))
        e = WebEvent(
            priority=WebEvent.Priority.MEDIUM,
            source=row[0],
            rfc931=row[1],
            authuser=row[2],
            time=timestamp,
            request=row[4],
            section=row[7],
            status=row[5],
            size=row[6],
            message="",
        )
        cls.processor.consume(e)
