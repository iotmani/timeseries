import heapq
import logging
from datetime import datetime
from collections import deque

from ..event import Event, WebLogEvent
from ..action import Action
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

        # Cache largest sliding window size as we'll use it often
        self._largestWindow = max(
            [calc.getWindowSize() for calc in self._statsCalculators]
        )
        # Assume events can come out of order for up to 2 seconds
        self._BUFFER_TIME = 2
        # Collect events in a heapq due to out-of-order arrival which is sometimes too late.
        self._buffer: list[WebLogEvent] = []
        # Collect sliding window events to count/discount in calculations as time progresses.
        self._events: deque[WebLogEvent] = deque()
        self._smallestBufferTime: int

    def consume(self, newestEvent: WebLogEvent) -> None:  # type: ignore
        """Consume sourced traffic entry, calculate stats and volume changes in traffic"""

        if self._events and self._events[-1].time >= newestEvent.time:
            logging.warning(
                f"Dropped log event as arrived more than {self._BUFFER_TIME}s late: {newestEvent}"
            )
            return

        heapq.heappush(self._buffer, newestEvent)
        if self._buffer:
            self._smallestBufferTime = min(newestEvent.time, self._buffer[0].time)
        else:
            self._smallestBufferTime = newestEvent.time
        # Check time diff between smallest (earliest) event and current
        seconds = newestEvent.time - self._smallestBufferTime
        # If still within buffer time, push new one to heap
        if not self._buffer or seconds <= self._BUFFER_TIME:
            logging.debug(
                f"Only buffered event, earliest {self._smallestBufferTime}, now: {newestEvent.time}, diff {seconds}"
            )
            return

        # discount all relevant events in buffer
        while newestEvent.time - self._buffer[0].time > self._BUFFER_TIME:
            e = heapq.heappop(self._buffer)
            logging.debug(f"Flushing from buffer {e.time}")

            # TODO change this to pair (time, [events]) ? so we remove all at once
            # TODO therefore add support to count multiple, and discount multiple
            self._events.append(e)
            # Remove all entries that fall out from start of the widest window interval,
            # updating calculations along the way
            self._removeOldEvents(e)

            # Add new event to calculations
            for calc in self._statsCalculators:
                calc.count(e)
        else:
            logging.debug(f"{e.time} is within buffer time")

        self._smallestBufferTime = self._buffer[0].time

    def _removeOldEvents(self, newestEvent: Event) -> None:
        "Remove one or more events that have fallen out of any calculators' time-intervals"

        # Remove from collected list of events
        while (
            self._events
            and newestEvent.time - self._events[0].time > self._largestWindow
        ):
            outdatedEvent = self._events.popleft()
            logging.debug(
                f"Removed outdated event {datetime.fromtimestamp(outdatedEvent.time)}."
            )
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
