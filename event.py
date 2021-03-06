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
        return f"{cls.time} {cls.message}"


@dataclass
class HTTPEvent(Event):
    """ Represents an individual HTTP event """

    rfc931: str
    authuser: str
    source: str
    request: str
    status: str
    size: str
    section: str

    def __repr__(cls) -> str:
        return f"{cls.__class__.__name__} {cls.time} {cls.priority.name}, "
        f"from {cls.source}, status={cls.status}, section={cls.section}"
