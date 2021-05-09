import os
import csv
import time
import typing
import logging
from .event import WebEvent
from .analyze import Processor
from datetime import datetime


class Parser:
    """ Extract raw log data into an event object """

    def __init__(self, processor: Processor):
        self.processor = processor

    def parse(self) -> None:
        """ Parsing implementation here """
        raise NotImplementedError()


class HTTPLogParser(Parser):
    """ Parses HTTP logs and generates WebEvent type of events """

    def __init__(self, processor: Processor, path: str, isMonitorMode: bool = False):
        super().__init__(processor)
        self._log = logging.getLogger(__name__)
        self._path = path
        self._isMonitorMode = isMonitorMode

    def parse(self) -> None:
        """ Parse raw data from log file and generate log event object """
        self._log.info(f"Monitoring HTTP log file {self._path}")
        position = 0
        while True:
            position = self._parseFile(position)
            if not self._isMonitorMode:
                break
            # Sleep for x seconds
            time.sleep(float(os.getenv("DD_LOG_MONITOR_TIME", 1.0)))

    def _parseFile(self, position: int = 0) -> int:
        try:
            with open(self._path, mode="r") as fd:
                fd.seek(position)
                logreader = csv.reader(fd)

                try:
                    # Skip header iff one exists
                    header = next(logreader)
                    if len(header) > 0 and header[0] != "remotehost":
                        self._log.debug("No header")
                        fd.seek(position)
                    else:
                        self._log.debug(f"Header: {header}")
                except StopIteration as e:
                    # E.g. Occurs if empty file or polling end of file
                    self._log.debug("Nothing further to read")
                    pass

                # Parse rows in best-effort mode (skip any bad lines)
                for row in logreader:
                    if self._isSanitised(row):
                        # and generate WebEvents to send for processing
                        self._generateEvent(row)
                return fd.tell()
        except FileNotFoundError as e:
            self._log.error(f"HTTP log file doesn't exist: {self._path}")
        except csv.Error as ce:
            self._log.error(f"HTTP log file not valid CSV: {self._path}")
        # Return original position if any issues
        return position

    def _isSanitised(self, row: typing.List[str]) -> bool:
        """ Sanitise row columns data types and parse data within as needed. """
        if len(row) != 7:
            self._log.warning(f"Malformed CSV row: {row}")
            return False

        # Parse section out of request, i.e. row[4]
        section = row[4].split(" ")
        if len(section) < 2 or len(section[1].split("/")) < 2:
            self._log.warning(f"Malformed 'section' part of row: {row}")
            return False
        row.append("/" + section[1].split("/")[1])

        try:
            datetime.fromtimestamp(int(row[3]))
        except (ValueError, OverflowError, OSError) as e:
            self._log.warning(f"Malformed 'date' part of row: {row}")
            return False

        return True

    def _generateEvent(self, row: typing.List[str]) -> None:
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
        self.processor.consume(e)
