from datetime import datetime
from dataclasses import dataclass
from enum import IntEnum


@dataclass
class Event:
    class Priority(IntEnum):
        LOW = 0
        MEDIUM = 1
        HIGH = 2
        SEVERE = 3

    time: datetime
    source: str
    priority: Priority

    def __repr__(cls) -> str:
        return "{0} {1} {2}, from {3}".format(
            cls.__class__.__name__, cls.time, cls.priority.name, cls.source
        )


@dataclass
class HTTPEvent(Event):
    rfc931: str
    authuser: str
    request: str
    status: int
    size: int
    section: str

    def __repr__(cls) -> str:
        return "{0} {1} {2}, from {3}, status={status}, section={section}".format(
            cls.__class__.__name__,
            cls.time,
            cls.priority.name,
            cls.source,
            status=cls.status,
            section=cls.section,
        )
