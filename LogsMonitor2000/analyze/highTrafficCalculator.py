import logging
from typing import Optional, Any
from ..event import Event
from ..action import Action
from datetime import datetime
from .calculator import StreamCalculator


class HighTrafficCalculator(StreamCalculator):
    "Trigger alert if average number of requests crosses the given threshold or returns back to normal"

    def __init__(
        self, action: Action, windowSizeInSeconds=120, highTrafficThreshold=10
    ):
        super().__init__(action, windowSizeInSeconds)

        self._threshold: int = highTrafficThreshold
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
        now = latestEvent.time
        # TODO io107
        timeInterval = self._windowSize
        # average = int(self._totalCount / max(1, timeInterval))
        average = self._totalCount

        logging.debug(f"High traffic average: {average}")
        # Fire only if average exceeds threshold
        if average > self._threshold and not self._alertMode:
            alertHighTraffic: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message="High traffic generated an alert - "
                f"hits {average}, triggered at {datetime.fromtimestamp(now)}",
            )
            self._action.notify(alertHighTraffic)
            self._alertMode = True
            logging.debug(f"High traffic, fired {alertHighTraffic}")

        # If back to normal again, alert only once
        if average <= self._threshold and self._alertMode:
            alertBackToNormal: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message=f"Traffic is now back to normal as of {datetime.fromtimestamp(now)}",
            )
            self._action.notify(alertBackToNormal)
            self._alertMode = False
            logging.debug(f"High traffic back to normal, fired {alertBackToNormal}")
