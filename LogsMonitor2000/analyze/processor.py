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
        else:
            logging.info("Most Common Stats calculator deactivated")

        # Only add calculator if parameters are valid
        if highTrafficThreshold > 0 and highTrafficInterval > 0:
            self._statsCalculators.append(
                HighTrafficCalculator(action, highTrafficInterval, highTrafficThreshold)
            )
        else:
            logging.info("High Traffic Alerts calculator deactivated")

        # Cache largest sliding window size as we'll use it often
        self._largestWindow = max(
            [calc.getWindowSize() for calc in self._statsCalculators]
        )
        # Assume events can come out of order for up to 2 seconds
        self._BUFFER_TIME = 2
        # Collect events in a heapq due to out-of-order arrival which is sometimes too late.
        self._buffer: list[WebLogEvent] = []
        # Collect sliding window events to count/discount in calculations as time progresses.
        self._events: deque[list[WebLogEvent]] = deque()

    def consume(self, newestEvent: WebLogEvent) -> None:  # type: ignore
        """Consume sourced traffic entry, calculate stats and volume changes in traffic"""

        if self._events and self._events[-1][0].time >= newestEvent.time:
            logging.warning(
                f"Dropped log event as arrived more than {self._BUFFER_TIME}s late: {newestEvent}"
            )
            return

        # Add to buffer heap, sorted by time
        heapq.heappush(self._buffer, newestEvent)

        # Check time diff between smallest (earliest) event and the current
        # If still within buffer time, nothing further to do
        earliestBufferEvent = min(newestEvent.time, self._buffer[0].time)
        timeDifference = newestEvent.time - earliestBufferEvent
        if not self._buffer or timeDifference <= self._BUFFER_TIME:
            logging.debug(
                f"Only buffered event, earliest {earliestBufferEvent}, now: {newestEvent.time}, diff {timeDifference}"
            )
            return

        eventGroups: list[list[WebLogEvent]] = []

        # Discount all events that occured beyond the buffer time
        while newestEvent.time - self._buffer[0].time > self._BUFFER_TIME:
            e = heapq.heappop(self._buffer)
            logging.debug(f"Flushing from buffer {e.time}")

            if eventGroups and e.time == eventGroups[-1][0].time:
                eventGroups[-1].append(e)
            else:
                eventGroups.append([e])

        for eventGroup in eventGroups:
            # Remove all entries that fall out from start of the widest window interval
            # updating calculations along the way
            self._removeOldEvents(eventGroup[0].time)

            self._events.append(eventGroup)

            # Add new event to calculations
            for calc in self._statsCalculators:
                for e in eventGroup:
                    calc.count(e)

    def _removeOldEvents(self, newestEventTime: int) -> None:
        "Remove one or more events that have fallen out of any calculators' time-intervals"
        # Remove from collected list of events
        while (
            self._events
            and newestEventTime - self._events[0][0].time > self._largestWindow
        ):
            outdatedEvents = self._events.popleft()
            for calc in self._statsCalculators:
                calc.discount(outdatedEvents, newestEventTime)

        # Starting from oldest event, let each calculator remove from its calculations any
        # events that have fallen outside its individual sliding window given the newest event time is the new 'now'
        for eventsGroup in self._events:
            isRemovedFromCalculation = False
            for calc in self._statsCalculators:
                if calc.discount(eventsGroup, newestEventTime):
                    isRemovedFromCalculation = True

            # Stop if all events discounted from every calculator's window
            if not isRemovedFromCalculation:
                return
