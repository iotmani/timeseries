import logging
from ..event import Event, WebLogEvent
from ..action import Action
from datetime import datetime


class StreamCalculator:
    "Interface for implementing different kinds of statistics calculation on a window of events"

    def __init__(self, action: Action, windowSizeInSeconds=10):
        # Time window required for calculations
        self._windowSize: int = windowSizeInSeconds

        # To trigger any alerts if needed
        self._action = action

        # Start time of sliding window specific to this calculator
        # Window could be smaller than the main window of collected events
        # Window is any time after this, i.e.:
        #   _windowStartsAfterEvent.time < newestEvent - _windowSize <= newestEvent
        self._windowStartsAfterEvent: int = -1

    def getWindowSize(self) -> int:
        "Time-window length this calculator requires to function"
        return self._windowSize

    def _isWithinWindow(self, old: int, new: int) -> bool:
        "Check if given event falls within window interval relative to the newest event"
        return new - old > self._windowSize and (
            self._windowStartsAfterEvent == -1 or old > self._windowStartsAfterEvent
        )

    def discount(self, eventsGroup: list[WebLogEvent], newestEventTime: int) -> bool:
        "Check event as it may or may not be in the sliding window, return true if removed"
        oldEventsTime = eventsGroup[0].time

        if self._isWithinWindow(old=oldEventsTime, new=newestEventTime):
            for e in eventsGroup:
                self._removeFromCalculation(e)
            self._windowStartsAfterEvent = oldEventsTime
            logging.debug(f"Removing outdated event(s) at {oldEventsTime}.")
            return True
        # We didn't delete anything as it was outside the window anyway
        return False

    def count(self, event: Event) -> None:
        "Consume an event as it enters in the sliding window interval"
        raise NotImplementedError()

    def _removeFromCalculation(self, event: Event) -> None:
        "Implement to perform the actual removal from overall calculation of out of window event"
        raise NotImplementedError()

    def _triggerAlert(self, eventTime: int) -> None:
        "Implement to check if conditions are met for sending any alerting"
        raise NotImplementedError()
