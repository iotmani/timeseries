import logging
import datetime
from typing import Optional, Any
from ..event import Event, WebLogEvent
from ..action import Action
from sortedcontainers import SortedList  # type: ignore
from .calculator import StreamCalculator
from .mostCommonCalculator import MostCommonCalculator
from .highTrafficCalculator import HighTrafficCalculator


class Processor:
    """ Collect and analyze log events, then trigger higher-level alerts """

    def __init__(self, action: Action):
        # Action to notify
        self._action = action

    def consume(self, event: Event) -> None:
        """ Consume log event and generate other events if applicable """
        raise NotImplementedError()


class AnalyticsProcessor(Processor):
    """
    Analyzes web-request log events and triggers alerts based on statistics
    e.g. the numbers of requests and their content.

    More specifically, this class implements the Processor interface and calls
    calculator functions on the stream of log events.
    """

    def __init__(
        self,
        action: Action,
        mostCommonStatsInterval=10,
        highTrafficThreshold=10,
        highTrafficInterval=120,
    ):
        super().__init__(action)
        # Initialize calculators, each with its own time-window size
        self._statsCalculators: list[StreamCalculator] = []
        if mostCommonStatsInterval > 0:
            self._statsCalculators.append(
                MostCommonCalculator(action, mostCommonStatsInterval)
            )

        # Only add calculator if its parameters are valid
        if highTrafficThreshold > 0 and highTrafficInterval > 0:
            self._statsCalculators.append(
                HighTrafficCalculator(action, highTrafficInterval, highTrafficThreshold)
            )

        # Cache max sliding window size as we'll use it often
        self._largestWindow = max(
            [calc.getWindowSize() for calc in self._statsCalculators]
        )
        # Collect events in a SortedList due to out-of-order possibility.
        self._events: Any = SortedList()

    def consume(self, newestEvent: Event) -> None:
        """Consume sourced traffic entry, calculate stats and volume changes in traffic"""

        self._events.add(newestEvent)

        # Remove all entries that fall out from start of the widest window interval,
        # updating calculations along the way
        self._removeOldEvents(newestEvent)

        # Add new event to calculations
        for calc in self._statsCalculators:
            calc.count(newestEvent)

    def _removeOldEvents(self, newestEvent: Event) -> None:
        "Remove one or more events that have fallen out of any calculators' time-intervals"

        # Remove from collected list of events
        while (
            self._events
            and newestEvent.time - self._events[0].time > self._largestWindow
        ):
            outdatedEvent = self._events.pop(0)
            logging.debug(f"Removed outdated event {outdatedEvent.time}.")
            for calc in self._statsCalculators:
                calc.discount(outdatedEvent, newestEvent)

        # Starting from oldest event, let each calculator remove from its calculations any
        # events that have fallen outside window intervals, given the newest one
        for e in self._events:
            isRemovedFromCalculation = False
            for calc in self._statsCalculators:
                if calc.discount(e, newestEvent):
                    isRemovedFromCalculation = True

            # Keep attempting until event is discounted from every calculator's window
            if not isRemovedFromCalculation:
                break
