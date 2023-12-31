import logging
from typing import Deque
from ..event import Event
from ..action import Action


class StreamCalculator:
    "Interface for implementing different kinds of statistics calculation on a window of events"

    def __init__(
        self, action: Action, events: Deque[list[Event]], windowSizeInSeconds=10
    ):

        # To trigger any alerts if needed
        self._action = action

        # Keep track of event last discounted by each calculator,
        # as sliding window sizes of events can be different.
        # Window is defined by time strictly greater than this last item removed and onwards
        self._lastRemovalTime: int = -1

        # Full list of collected events
        self._events = events

        # Time window required for calculations
        self.windowSize: int = windowSizeInSeconds

    def _isNoLongerWithinWindow(self, old: int, new: int) -> bool:
        """
        Return true if event now falls outside window interval,
        relative to the latest event as well as the previously removed
        """
        return new - old > self.windowSize and (
            self._lastRemovalTime == -1 or old > self._lastRemovalTime
        )

    def discountIfOut(self, olderEventsGrp: list[Event], newestEventTime: int) -> bool:
        """
        Check event as it may no longer be in the sliding window:
        * It may have already been removed (i.e. earlier than _lastRemovalTime) => return False.
        * It may be within the window time-interavl, not to be removed => return False.
        * It may only now be outside the window, and is after last removel => Remove it and return True.
        """
        oldEventsTime = olderEventsGrp[0].time

        if self._isNoLongerWithinWindow(old=oldEventsTime, new=newestEventTime):
            self.discount(olderEventsGrp)
            self._lastRemovalTime = oldEventsTime
            logging.debug(f"Removing outdated event(s) at {oldEventsTime}.")
            return True
        # We didn't discount anything as it was already removed or valid within window
        return False

    def count(self, events: list[Event]) -> None:
        "Consume an event as it enters in the sliding window interval"
        raise NotImplementedError()

    def discount(self, events: list[Event]) -> None:
        "Perform the actual removal from overall calculation of out of window event"
        raise NotImplementedError()

    def triggerAlert(self, eventTime: int) -> None:
        "If conditions are met, trigger alert"
        raise NotImplementedError()
