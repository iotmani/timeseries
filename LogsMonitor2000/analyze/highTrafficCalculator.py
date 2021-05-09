import logging
import datetime
from typing import Optional, Any
from ..event import Event
from ..action import Action
from .calculator import StreamCalculator


class HighTrafficCalculator(StreamCalculator):
    "Trigger alert if average number of requests crosses the given threshold or returns back to normal"

    def __init__(
        self, action: Action, windowSizeInSeconds=120, highTrafficAvgThreshold=10
    ):
        super().__init__(action, windowSizeInSeconds)

        self._threshold: int = highTrafficAvgThreshold
        self._alertMode = False
        self._totalCount: int = 0

    def count(self, e: Event) -> None:
        "Count to use in high traffic average"
        self._totalCount += 1
        self._triggerAlert(e)

    def _removeFromCalculation(self, e: Event) -> None:
        self._totalCount -= 1
        self._triggerAlert(e)

    def _triggerAlert(self, latestEvent: Event) -> None:

        if self._windowSize < datetime.timedelta(0):
            # Negative interval, skip check
            logging.debug("High traffic checks deactivated")
            return

        now = latestEvent.time

        timeInterval = self._windowSize.total_seconds()
        # average = int(self._totalCount / max(1, timeInterval))
        average = self._totalCount

        logging.debug(f"High traffic average: {average}")
        # Fire only if average exceeds threshold
        if average > self._threshold and not self._alertMode:
            alertHighTraffic: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message="High traffic generated an alert - "
                f"hits {average}, triggered at {now}",
            )
            self._action.notify(alertHighTraffic)
            self._alertMode = True
            logging.debug(f"High traffic, fired {alertHighTraffic}")

        # If back to normal again, alert only once
        if average <= self._threshold and self._alertMode:
            alertBackToNormal: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message=f"Traffic is now back to normal as of {now}",
            )
            self._action.notify(alertBackToNormal)
            self._alertMode = False
            logging.debug(f"High traffic back to normal, fired {alertBackToNormal}")
