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

    def __repr__(cls) -> str:
        return "{name} {time} - {message}".format(
            name=cls.__class__.__name__, time=cls.time, message=cls.message
        )


@dataclass
class HTTPEvent(Event):
    """ Represents an individual HTTP event """

    rfc931: str
    authuser: str
    source: str
    request: str
    status: int
    size: int
    section: str

    def __repr__(cls) -> str:
        return "{name} {time} {priority}, from {source}, status={status}, section={section}".format(
            name=cls.__class__.__name__,
            time=cls.time,
            source=cls.source,
            status=cls.status,
            section=cls.section,
            priority=cls.priority.name,
        )
