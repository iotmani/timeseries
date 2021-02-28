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
    priority: Priority = Priority.MEDIUM

    def __repr__(cls) -> str:
        return "{0} {1} {2}, from {3}".format(
            cls.__class__.__name__, cls.time, cls.priority.name, cls.source
        )


class HTTPEvent(Event):
    rfc931: str = None
    authuser: str = None
    request: str = None
    status: int = None
    size: int = None