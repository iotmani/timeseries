import logging
from action import Action
from event import Event, HTTPEvent
from typing import List


class Processor:
    def __init__(cls, action: Action):
        cls.action = action

    def consume(cls, event: Event) -> None:
        raise NotImplementedError()


class HTTPEventProcessor(Processor):
    def __init__(cls, action: Action):
        super().__init__(action)
        logging.basicConfig(level=logging.INFO)

    """ Collects and anlyzes http events """

    def consume(cls, event: HTTPEvent) -> None:
        cls.action.notify(event)

    def consume(cls, events: List[HTTPEvent]) -> None:
        [cls.action.notify(event) for event in events]
