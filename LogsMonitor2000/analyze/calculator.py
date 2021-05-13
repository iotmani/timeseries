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

        # Window could be smaller than the largest calculator window size of collected events
        # Window is any time after this, i.e.:
        #   _lastRemovalTime < newestEvent - _windowSize <= newestEvent
        self._lastRemovalTime: int = -1

    def getWindowSize(self) -> int:
        "Time-window length this calculator requires to function"
        return self._windowSize

    def _isWithinWindow(self, old: int, new: int) -> bool:
        "Check if given event falls within window interval relative to the newest event"
        return new - old > self._windowSize and (
            self._lastRemovalTime == -1 or old > self._lastRemovalTime
        )

    def discountIfOut(self, eventsGroup: list[Event], newestEventTime: int) -> bool:
        "Check event as it may or may not be in the sliding window, return true if removed"
        oldEventsTime = eventsGroup[0].time

        if self._isWithinWindow(old=oldEventsTime, new=newestEventTime):
            self.discount(eventsGroup)
            self._lastRemovalTime = oldEventsTime
            logging.debug(f"Removing outdated event(s) at {oldEventsTime}.")
            return True
        # We didn't delete anything as it was outside the window anyway
        return False

    def count(self, events: list[Event]) -> None:
        "Consume an event as it enters in the sliding window interval"
        raise NotImplementedError()

    def discount(self, events: list[Event]) -> None:
        "Implement to perform the actual removal from overall calculation of out of window event"
        raise NotImplementedError()

    def _triggerAlert(self, eventTime: int) -> None:
        "Implement to check if conditions are met for alerting"
        raise NotImplementedError()
