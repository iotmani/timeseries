import logging
from datetime import datetime
from typing import Counter
from ..event import Event, WebLogEvent
from ..action import Action
from .calculator import StreamCalculator
from collections import Counter


class MostCommonCalculator(StreamCalculator):
    "Keeps track of most common source, most common section in a given time-interval"

    def __init__(self, action: Action, windowSizeInSeconds=10):
        super().__init__(action, windowSizeInSeconds)

        # Collect stats every x seconds
        self._timeLastCollectedStats: int = -1

        # Counters to display
        self._countSections: Counter[str] = Counter()
        self._countSources: Counter[str] = Counter()

    def discount(self, e: WebLogEvent) -> None:  # type: ignore
        if type(e) is not WebLogEvent:
            raise ValueError(f"Expected WebLogEvent for: {e}")
        logging.debug(
            f"Removing old event from most common stats: {datetime.fromtimestamp(e.time)}"
        )
        self._countSections[e.section] -= 1
        self._countSources[e.source] -= 1
        # No need to update calculation for this calculator at 'discount'
        # Alerts can only be generated when we add a new one

    def count(self, e: WebLogEvent) -> None:  # type: ignore
        if type(e) is not WebLogEvent:
            raise ValueError(f"Expected WebLogEvent for: {e}")

        logging.debug(
            f"Counting log {e.section} from {e.source} at {datetime.fromtimestamp(e.time)}"
        )
        self._countSections[e.section] += 1
        self._countSources[e.source] += 1
        self._triggerAlert(e.time)

    def _triggerAlert(self, latestEventTime: int) -> None:
        """ Refresh calculation, trigger alerts with most common sections/sources when applicable """
        if self._timeLastCollectedStats == -1:
            self._timeLastCollectedStats = latestEventTime
        if (latestEventTime - self._timeLastCollectedStats) < self._windowSize:
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