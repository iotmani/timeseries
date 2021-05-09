import logging
import datetime
from typing import Optional
from ..event import Event
from ..action import Action


class StreamCalculator:
    "Interface for implementing different kinds of statistics calculation on a window of events"

    def __init__(self, action: Action, windowSizeInSeconds=10):
        # Time window required for calculations
        self._windowSize = datetime.timedelta(seconds=windowSizeInSeconds)

        # To trigger any alerts if needed
        self._action = action

        # Start time of sliding window specific to this calculator
        # Window could be smaller than the main window of collected events
        # Window is any time after this, i.e.:
        #   _windowStartsAfterEvent.time < newestEvent - _windowSize <= newestEvent
        self._windowStartsAfterEvent: Optional[Event] = None

    def getWindowSize(self) -> datetime.timedelta:
        "Time-window length this calculator requires to function"
        return self._windowSize

    def _isWithinWindow(self, oldEvent: Event, newestEvent: Event) -> bool:
        "Check if given event falls within window interval relative to the newest event"
        return newestEvent.time - oldEvent.time <= self._windowSize and (
            self._windowStartsAfterEvent is None
            # TODO this used to be <=
            or (
                oldEvent.time > self._windowStartsAfterEvent.time
                and oldEvent != self._windowStartsAfterEvent
            )
        )

    def discount(self, e: Event, newestEvent) -> bool:
        "Check event as it may or may not the sliding window, return true if it did"
        if self._isWithinWindow(oldEvent=e, newestEvent=newestEvent):
            self._removeFromCalculation(e)
            self._windowStartsAfterEvent = e
            return True
        # We didn't delete anything as it was outside the window anyway
        return False

    def count(self, event: Event) -> None:
        "Consume an event as it enters in the sliding window interval"
        raise NotImplementedError()

    def _removeFromCalculation(self, event: Event) -> None:
        "Implement to perform the actual removal from overall calculation of out of window event"
        raise NotImplementedError()

    def _triggerAlert(self, event: Event) -> None:
        "Implement to check if conditions are met for sending any alerting"
        raise NotImplementedError()
