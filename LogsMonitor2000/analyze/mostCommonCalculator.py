import logging
from typing import Counter
from ..event import Event, WebLogEvent
from ..action import Action
from .calculator import StreamCalculator
from collections import Counter


class MostCommonCalculator(StreamCalculator):
    "Keeps track of most common source, most common section in a given time-interval"

    def __init__(self, action: Action, events, windowSizeInSeconds=10):
        super().__init__(action, events, windowSizeInSeconds)

        # Collect stats every x seconds
        self._timeLastCollectedStats: int = -1

        # Counters to display
        self._countSections: Counter[str] = Counter()
        self._countSources: Counter[str] = Counter()

    def discount(self, events: list[WebLogEvent]) -> None:  # type: ignore
        if type(events[0]) is not WebLogEvent:
            raise ValueError(f"Expected WebLogEvent for: {events}")

        for e in events:
            logging.debug(f"Removing old event from most common stats: {e.time}")
            self._countSections[e.section] -= 1
            self._countSources[e.source] -= 1
            # No need to update calculation for this calculator at 'discount'
            # Alerts for this are only meaningful when we add a new one in case it puts us at a new interval

    def count(self, events: list[WebLogEvent]) -> None:  # type: ignore
        if type(events[0]) is not WebLogEvent:
            raise ValueError(f"Expected WebLogEvent for: {events}")

        for e in events:
            logging.debug(f"Counting log {e.section} from {e.source} at {e.time}")
            self._countSections[e.section] += 1
            self._countSources[e.source] += 1

    def triggerAlert(self, latestEventTime: int) -> None:
        """ Refresh calculation, trigger alerts with most common sections/sources when applicable """
        if self._timeLastCollectedStats == -1:
            self._timeLastCollectedStats = latestEventTime
        if (latestEventTime - self._timeLastCollectedStats) < self.windowSize:
            # Latest event time hasn't yet crossed the full interval
            return

        mostCommonSection = self._countSections.most_common(1)[0]
        mostCommonSource = self._countSources.most_common(1)[0]

        statsEvent = Event(
            priority=Event.Priority.MEDIUM,
            message="Most common section: "
            + f"{mostCommonSection[0]} ({mostCommonSection[1]} requests)"
            + ", source: "
            + f"{mostCommonSource[0]} ({mostCommonSource[1]} requests)",
            time=latestEventTime,
        )
        self._action.notify(statsEvent)
        self._timeLastCollectedStats = latestEventTime
        logging.debug(f"Fired stats alert {statsEvent}")