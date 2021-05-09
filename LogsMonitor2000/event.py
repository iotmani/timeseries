import enum
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Event:
    """ Represents an individual event """

    class Priority(enum.IntEnum):
        LOW = 0
        MEDIUM = 1
        HIGH = 2
        SEVERE = 3

    time: datetime
    message: str
    priority: Priority

    def __lt__(self, other) -> bool:
        " Ordered by time by default "
        return self.time < other.time

    def __repr__(self) -> str:
        return f"{self.time} {self.message}"


@dataclass
class WebLogEvent(Event):
    """ Represents an individual Web traffic event """

    rfc931: str
    authuser: str
    source: str
    request: str
    status: str
    size: str
    section: str
