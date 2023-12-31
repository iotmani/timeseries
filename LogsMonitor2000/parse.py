import os
import csv
import time
import logging
from .event import WebLogEvent
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
    """ Parses HTTP logs and generates WebLogEvent type of events """

    def __init__(self, processor: Processor, path: str, isFollowMode: bool = False):
        super().__init__(processor)
        self._path = path
        self._isFollowMode = isFollowMode

    def parse(self) -> None:
        """ Parse raw data from log file and generate log event object """
        logging.info(f"Monitoring HTTP log file {self._path}")
        position = 0
        while True:
            position = self._parseFile(position)
            if self._isFollowMode:
                # Sleep for x seconds
                time.sleep(float(os.getenv("DD_LOG_MONITOR_TIME", 1.0)))
            else:
                # Run only once
                break

    def _parseFile(self, position: int = 0) -> int:
        try:
            with open(self._path, mode="r") as fd:
                fd.seek(position)
                logreader = csv.reader(fd)

                try:
                    # Skip header iff one exists
                    header = next(logreader)
                    if len(header) > 0 and header[0] != "remotehost":
                        logging.debug("No header")
                        fd.seek(position)
                    else:
                        logging.debug(f"Header: {header}")
                except StopIteration as e:
                    # E.g. Occurs if empty file or polling end of file
                    logging.debug("Nothing further to read")
                    pass

                # Parse rows in best-effort mode (i.e. skip any bad lines)
                for row in logreader:
                    if self._isSanitised(row):
                        # and generate WebLogEvents to send for processing
                        self._generateEvent(row)
                # Flush buffer
                self.processor.consume(None)
                return fd.tell()
        except FileNotFoundError as e:
            logging.error(f"HTTP log file doesn't exist: {self._path}")
        except csv.Error as ce:
            logging.error(f"HTTP log file not valid CSV: {self._path}")
        # Return original to position if any issues so we stop or keep polling
        return position

    def _isSanitised(self, row: list[str]) -> bool:
        """ Sanitise row columns data types """
        if len(row) != 7:
            logging.warning(f"Malformed CSV row: {row}")
            return False

        # Parseable section out of request, i.e. row[4]
        section = row[4].split(" ")
        if len(section) < 2 or len(section[1].split("/")) < 2:
            logging.warning(f"Malformed 'section' part of row: {row}")
            return False

        try:
            datetime.fromtimestamp(int(row[3]))
        except (ValueError, OverflowError, OSError) as e:
            logging.warning(f"Malformed 'date' part of row: {row}")
            return False

        return True

    def _generateEvent(self, row: list[str]) -> None:
        """ Build event object from pre-sanitised data and send for processing """

        section = "/" + row[4].split(" ")[1].split("/")[1]
        e = WebLogEvent(
            priority=WebLogEvent.Priority.MEDIUM,
            source=row[0],
            rfc931=row[1],
            authuser=row[2],
            time=int(row[3]),
            request=row[4],
            section=section,
            status=row[5],
            size=row[6],
            message="",
        )
        self.processor.consume(e)
