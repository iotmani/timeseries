import heapq
import logging
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
        """ Consume log event and generate other events (alerts) if applicable """
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
        # Initialize calculators, each with its own time-window size
        self._statsCalculators: list[StreamCalculator] = []
        if mostCommonStatsInterval > 0:
            self._statsCalculators.append(
                MostCommonCalculator(action, mostCommonStatsInterval)
            )
        else:
            logging.info("Most Common Stats calculator deactivated")

        # Add calculator if its parameters are valid
        if highTrafficThreshold > 0 and highTrafficInterval > 0:
            self._statsCalculators.append(
                HighTrafficCalculator(action, highTrafficInterval, highTrafficThreshold)
            )
        else:
            logging.info("High Traffic Alerts calculator deactivated")

        # Cache largest sliding window size as we'll use it often
        self._largestWindow = max([calc.windowSize for calc in self._statsCalculators])

        # Assume events can come out of order for up to 2 seconds
        self._BUFFER_TIME = 2

        # Collect events in a heapq due to buffer out-of-order arrivals before processing them
        self._buffer: list[Event] = []

        # Collect sliding window events to count/discount in calculations as time progresses
        # We often pop-left and append-right hence deque
        # We expect lots of events per second, therefore batch them together
        self._events: deque[list[Event]] = deque()

    def consume(self, latestEvent: WebLogEvent) -> None:  # type: ignore
        """Consume sourced traffic entry, calculate stats and volume changes in traffic"""

        if self._events and self._events[-1][0].time >= latestEvent.time:
            logging.warning(
                f"Dropped log event as arrived more than {self._BUFFER_TIME}s late: {latestEvent}"
            )
            return

        # Add to buffer heap, sorted by time
        heapq.heappush(self._buffer, latestEvent)

        # Check time diff between smallest (earliest) buffer event and the current
        # If still within buffer time, nothing further to do
        earliestBufferEvent = min(latestEvent.time, self._buffer[0].time)
        timeDifference = latestEvent.time - earliestBufferEvent
        if not self._buffer or timeDifference <= self._BUFFER_TIME:
            logging.debug(f"Buffered event {latestEvent.time}, diff {timeDifference}")
            return

        eventGroups: list[list[Event]] = []

        # Flush events with time beyond the buffer time
        while latestEvent.time - self._buffer[0].time > self._BUFFER_TIME:

            e = heapq.heappop(self._buffer)

            # If previous (-1) event has same occurence time, group with it
            if eventGroups and e.time == eventGroups[-1][0].time:
                eventGroups[-1].append(e)
                logging.debug(f"Flushed from buffer another: {e.time}")
            else:
                logging.debug(f"Flushed from buffer event:   {e.time}")
                eventGroups.append([e])

        for eventGroup in eventGroups:
            # Given latest event time, remove all entries that fall out from start of the _largestWindow interval
            # updating calculations along the way
            self._removeOldEvents(eventGroup[0].time)

            self._events.append(eventGroup)

            # Add new event to calculations
            for calc in self._statsCalculators:
                calc.count(eventGroup)

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
