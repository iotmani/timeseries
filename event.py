from datetime import datetime
from dataclasses import dataclass


@dataclass
class Event:
    time: datetime
    source: str

    def __repr__(cls) -> str:
        return "{0} {1}, from {2}".format(cls.__class__.__name__, cls.time, cls.source)


class HTTPEvent(Event):
    rfc931: str = None
    authuser: str = None
    request: str = None
    status: int = None
    size: int = None