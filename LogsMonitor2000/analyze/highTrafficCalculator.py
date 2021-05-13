import logging
from ..event import Event
from ..action import Action
from datetime import datetime, timedelta
from .calculator import StreamCalculator


class HighTrafficCalculator(StreamCalculator):
    "Trigger alert if average number of requests crosses the given threshold or returns back to normal"

    def __init__(
        self, action: Action, windowSizeInSeconds=120, highTrafficThreshold=10
    ):
        super().__init__(action, windowSizeInSeconds)
        self._threshold: int = highTrafficThreshold

        # Total number of events in sliding window
        self._totalCount: int = 0

        # Store if in high-traffic alert mode
        self._isHighAlert = False

    def count(self, events: list[Event]) -> None:
        "Count to use in high traffic average"
        self._totalCount += len(events)
        self._triggerAlert(events[0].time)

    def discount(self, events: list[Event]) -> None:
        "Discount and check if avg back to normal"
        self._totalCount -= len(events)
        self._triggerAlert(events[0].time)

    def _triggerAlert(self, now: int) -> None:
        """
        If average above threshold, alert once until recovery.
        If average back below threshold, alert once that it's recovered.
        """

        average = int(self._totalCount / max(1, self.windowSize))
        logging.debug(f"High traffic average: {average}")

        # Fire only if average exceeds threshold, alert only once
        if average > self._threshold and not self._isHighAlert:
            alertHighTraffic: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message="High traffic generated an alert - "
                f"hits {average}, triggered at {datetime.fromtimestamp(now)}",
            )
            self._action.notify(alertHighTraffic)
            self._isHighAlert = True
            logging.debug(f"High traffic, fired {alertHighTraffic}")

        # If back to normal again
        if average <= self._threshold and self._isHighAlert:
            alertBackToNormal: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message=f"Traffic is now back to normal as of {datetime.fromtimestamp(now)}",
            )
            self._action.notify(alertBackToNormal)
            self._isHighAlert = False
            logging.debug(f"High traffic back to normal, fired {alertBackToNormal}")
