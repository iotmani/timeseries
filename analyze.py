import logging
from typing import List
from action import Action
from event import Event, HTTPEvent


class Processor:
    """ Collects and anlyzes parsed events """

    def __init__(cls, action: Action):
        cls.action = action

    def consume(cls, event: Event) -> None:
        raise NotImplementedError()


class HTTPEventProcessor(Processor):
    """ Collects and anlyzes parsed HTTP events """

    def __init__(cls, action: Action):
        super().__init__(action)
        logging.basicConfig(level=logging.INFO)

    def consume(cls, event: HTTPEvent) -> None:
        cls.action.notify(event)

    def consumeBatch(cls, events: List[HTTPEvent]) -> None:
        [cls.action.notify(event) for event in events]
