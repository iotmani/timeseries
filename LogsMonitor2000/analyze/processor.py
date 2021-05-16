import heapq
import logging
from typing import Optional, Deque
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

    def consume(self, event: Optional[Event]) -> None:
        """
        Consume log event and generate other events (alerts) if applicable.
        A None event value is a noop or buffer flush.
        """
        raise NotImplementedError()


class AnalyticsProcessor(Processor):
    """
    Analyzes Web request log events and triggers alerts based on statistics
    e.g. Average numbers of requests beyond threshold.

    More specifically, this class implements the Processor interface and calls
    calculator functions on the stream of log events.
    """

    def __init__(
        self,
        action: Action,
        mostCommonStatsInterval=10,
        highTrafficInterval=120,
        highTrafficThreshold=10,
    ):
        super().__init__(action)

        # Collect sliding window events to count/discount in calculations as time progresses
        # We often pop-left and append-right hence deque
        # We expect lots of events per second, therefore batch them together
        self._events: Deque[list[Event]] = deque()

        # Initialize calculators, each with its own time-window size
        self._statsCalculators: list[StreamCalculator] = []
        if mostCommonStatsInterval > 0:
            self._statsCalculators.append(
                MostCommonCalculator(action, self._events, mostCommonStatsInterval)
            )
        else:
            logging.info("Most Common Stats calculator deactivated")

        # Add calculator if its parameters are valid
        if highTrafficThreshold > 0 and highTrafficInterval > 0:
            self._statsCalculators.append(
                HighTrafficCalculator(
                    action, self._events, highTrafficInterval, highTrafficThreshold
                )
            )
        else:
            logging.info("High Traffic Alerts calculator deactivated")

        # Cache largest sliding window size as we'll use it often
        self._largestWindow = max([calc.windowSize for calc in self._statsCalculators])

        # Assume events can come out of order for up to 2 seconds
        self._BUFFER_TIME = 2

        # Collect events in a heapq due to buffer out-of-order arrivals before processing them
        self._buffer: list[Event] = []

    def consume(self, latestEvent: Optional[WebLogEvent]) -> None:  # type: ignore
        """Consume sourced traffic entry, calculate stats and volume changes in traffic"""
        if latestEvent is None:
            # None event value is considered a full flush of buffer, i.e. at EOF.
            # None parameter is passed instead of defaulting to it makes the intent more explicit IMO.
            self._bufferFlush(None)
            return

        if self._events and self._events[-1][0].time > latestEvent.time:
            logging.warning(
                f"Event {latestEvent.time} dropped due to >{self._BUFFER_TIME}s late"
            )
            return

        # Add to buffer, ordered by time
        heapq.heappush(self._buffer, latestEvent)

        # Flush any "old-enough" items from buffer for processing
        self._bufferFlush(latestEvent)

    def _bufferFlush(self, latestEvent: Optional[WebLogEvent]) -> None:

        # To store events grouped and sorted by time
        eventGroups: list[list[Event]] = []

        # Flush the events that occured beyond the buffer time duration
        while self._buffer and (
            # None event value is considered a full buffer flush, i.e. at EOF.
            latestEvent is None
            or latestEvent.time - self._buffer[0].time > self._BUFFER_TIME
        ):

            e = heapq.heappop(self._buffer)

            # If previous (-1st) event has same occurence time, group with it
            if eventGroups and e.time == eventGroups[-1][0].time:
                eventGroups[-1].append(e)
                logging.debug(f"Flushed from buffer another: {e.time}")
            else:
                logging.debug(f"Flushed from buffer event:   {e.time}")
                eventGroups.append([e])

        for eventGroup in eventGroups:
            self._events.append(eventGroup)

            # Given latest event time, remove all entries that fall out from start of the _largestWindow interval
            # updating calculations along the way
            self._removeOldEvents(eventGroup[0].time)

            # Add new event to calculations
            for calc in self._statsCalculators:
                calc.count(eventGroup)

            # Generate alerts if applicable
            for calc in self._statsCalculators:
                calc.triggerAlert(eventGroup[0].time)

    def _removeOldEvents(self, newestEventTime: int) -> None:
        "Remove one or more events that have fallen out of any calculators' sliding window"

        # From oldest events-group time first, remove from collected list of events
        # if they're now out of the larger window (shared memory)
        while (
            self._events
            and newestEventTime - self._events[0][0].time > self._largestWindow
        ):
            outdatedEventsGroup = self._events.popleft()

            for calc in self._statsCalculators:
                calc.discountIfOut(outdatedEventsGroup, newestEventTime)

        # Handle smaller sliding-windows:
        # Starting from oldest event, let each calculator remove any events that
        # have fallen outside its individual sliding window given the new 'now'
        for eventsGroup in self._events:
            isRemovedFromCalculation = False
            for calc in self._statsCalculators:
                if calc.discountIfOut(eventsGroup, newestEventTime):
                    isRemovedFromCalculation = True

            # Stop if all calculator are done discounting
            if not isRemovedFromCalculation:
                return
