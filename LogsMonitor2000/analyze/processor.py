import logging
import datetime
from typing import Optional, Any
from ..event import Event, WebEvent
from ..action import Action
from .calculator import WindowedCalculator, MostCommonCalculator, HighTrafficCalculator
from sortedcontainers import SortedList  # type: ignore


class Processor:
    """ Collect and analyze log events, then trigger higher-level alerts """

    def __init__(cls, action: Action):
        # Action to notify
        cls._action = action

    def consume(cls, event: Event) -> None:
        """ Consume log event and generate other events if applicable """
        raise NotImplementedError()


class StatsProcessor(Processor):
    """
    Analyzes web-request events and triggers alerts based on statistics around
    the numbers of requests and their content.

    More specifically, this class implements the Processor interface and calls
    different stats calculators on the collected set of events to process.
    """

    def __init__(
        cls,
        action: Action,
        mostCommonStatsInterval=10,
        highTrafficAvgThreshold=10,
        highTrafficInterval=120,
    ):
        super().__init__(action)
        # Initialize calculators, each with its own time-window size
        cls._statsCalculators = [
            MostCommonCalculator(action, mostCommonStatsInterval),
            HighTrafficCalculator(action, highTrafficInterval, highTrafficAvgThreshold),
        ]
        # Cache max sliding window size
        cls._widestWindowSize = max(
            [calc.getWindowSize() for calc in cls._statsCalculators]
        )
        # Collect events in a SortedList due to out-of-order possibility.
        cls._events: Any = SortedList()

        cls._isFirst = False

    def consume(cls, newestEvent: Event) -> None:
        """Consume sourced traffic entry, calculate stats and volume changes in traffic"""

        cls._events.add(newestEvent)

        # Remove all entries that fall out from start of the widest window interval,
        # updating calculations along the way
        cls._removeOldEvents(newestEvent)

        # Add new event to calculations
        for calc in cls._statsCalculators:
            calc.count(newestEvent)

    def _removeOldEvents(cls, newestEvent: Event) -> None:
        "Remove one or more events that have fallen out of any calculators' time-intervals"

        # Remove from collected list of events
        while (
            cls._events
            and newestEvent.time - cls._events[0].time > cls._widestWindowSize
        ):
            outdatedEvent = cls._events.pop(0)
            logging.debug(f"Removed outdated event {outdatedEvent.time}.")
            for calc in cls._statsCalculators:
                calc.discount(outdatedEvent, newestEvent)

        # Starting from oldest event, let each calculator remove from its calculations any
        # events that have fallen outside window intervals, given the newest one
        for e in cls._events:
            isRemovedFromCalculation = False
            for calc in cls._statsCalculators:
                if calc.discount(e, newestEvent):
                    isRemovedFromCalculation = True

            # Keep attempting until event is discounted from every calculator's window
            if not isRemovedFromCalculation:
                break
