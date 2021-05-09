import logging
import datetime
from typing import Counter, Optional, Any
from ..event import Event, WebEvent
from ..action import Action
from .calculator import StreamCalculator
from collections import Counter


class MostCommonCalculator(StreamCalculator):
    "Keeps track of most common source, most common section in a given time-interval"

    def __init__(cls, action: Action, windowSizeInSeconds=10):
        super().__init__(action, windowSizeInSeconds)

        # Used for counting "most common" traffic stats
        cls._timeLastCollectedStats: Optional[datetime.datetime] = None
        cls._countSections: Counter[str] = Counter()
        cls._countSources: Counter[str] = Counter()

    def _removeFromCalculation(cls, e: WebEvent) -> None:  # type: ignore
        if type(e) is not WebEvent:
            raise ValueError(f"Expected WebEvent for: {e}")
        logging.debug(f"Removing old event from most common stats: {e.time}")
        cls._countSections[e.section] -= 1
        cls._countSources[e.source] -= 1
        # No need to update calculation for this calculator at 'discount'
        # Alerts can only be generated when we add a new one

    def count(cls, e: WebEvent) -> None:  # type: ignore
        if type(e) is not WebEvent:
            raise ValueError(f"Expected WebEvent for: {e}")

        logging.debug(f"Counting log {e.section} from {e.source} at {e.time}")
        cls._countSections[e.section] += 1
        cls._countSources[e.source] += 1
        cls._triggerAlert(e)

    def _triggerAlert(cls, latestEvent: Event) -> None:
        """ Refresh calculation, trigger alerts with most common sections/sources when applicable """

        if cls._windowSize < datetime.timedelta(0):
            # Negative interval -> Stats calculation are deactivated
            return

        cls._timeLastCollectedStats = cls._timeLastCollectedStats or latestEvent.time
        if (latestEvent.time - cls._timeLastCollectedStats) < cls._windowSize:
            # Latest event time hasn't yet crossed the full interval
            return

        mostCommonSection = cls._countSections.most_common(1)[0]
        mostCommonSource = cls._countSources.most_common(1)[0]

        statsEvent = Event(
            priority=Event.Priority.MEDIUM,
            message="Most common section: "
            + f"{mostCommonSection[0]} ({mostCommonSection[1]} requests)"
            + ", source: "
            + f"{mostCommonSource[0]} ({mostCommonSource[1]} requests)",
            time=latestEvent.time,
        )
        cls._action.notify(statsEvent)
        logging.debug(f"Fired stats alert {statsEvent}")
        cls._timeLastCollectedStats = latestEvent.time