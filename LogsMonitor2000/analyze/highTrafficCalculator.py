import logging
import datetime
from typing import Optional, Any
from ..event import Event
from ..action import Action
from .calculator import StreamCalculator


class HighTrafficCalculator(StreamCalculator):
    "Trigger alert if average number of requests crosses the given threshold or returns back to normal"

    def __init__(
        cls, action: Action, windowSizeInSeconds=120, highTrafficAvgThreshold=10
    ):
        super().__init__(action, windowSizeInSeconds)

        cls._threshold: int = highTrafficAvgThreshold
        cls._alertMode = False
        cls._totalCount: int = 0

    def count(cls, e: Event) -> None:
        "Count to use in high traffic average"
        cls._totalCount += 1
        cls._triggerAlert(e)

    def _removeFromCalculation(cls, e: Event) -> None:
        cls._totalCount -= 1
        cls._triggerAlert(e)

    def _triggerAlert(cls, latestEvent: Event) -> None:

        if cls._windowSize < datetime.timedelta(0):
            # Negative interval, skip check
            logging.debug("High traffic checks deactivated")
            return

        now = latestEvent.time

        timeInterval = cls._windowSize.total_seconds()
        # average = int(cls._totalCount / max(1, timeInterval))
        average = cls._totalCount

        logging.debug(f"High traffic average: {average}")
        # Fire only if average exceeds threshold
        if average > cls._threshold and not cls._alertMode:
            alertHighTraffic: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message="High traffic generated an alert - "
                f"hits {average}, triggered at {now}",
            )
            cls._action.notify(alertHighTraffic)
            cls._alertMode = True
            logging.debug(f"High traffic, fired {alertHighTraffic}")

        # If back to normal again, alert only once
        if average <= cls._threshold and cls._alertMode:
            alertBackToNormal: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message=f"Traffic is now back to normal as of {now}",
            )
            cls._action.notify(alertBackToNormal)
            cls._alertMode = False
            logging.debug(f"High traffic back to normal, fired {alertBackToNormal}")
