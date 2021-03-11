import logging
import datetime
from os import getenv
from event import Event, WebEvent
from action import Action
from typing import Counter, Optional, Any
from collections import Counter
from sortedcontainers import SortedList  # type: ignore


class Processor:
    """ Collect and analyze log events, then trigger higher-level alerts """

    def __init__(cls, action: Action):
        # Action to notify
        cls._action = action

    def consume(cls, event: Event) -> None:
        """ Consume log event and generate other events if applicable """
        raise NotImplementedError()


class StatsProcessor(Processor):
    """
    Analyzes web-request events and triggers alerts based on statistics around
    the numbers of requests and their content.

    More specifically, this class implements the Processor interface and calls
    different stats calculators on the collected set of events to process.
    """

    def __init__(
        cls,
        action: Action,
        mostCommonStatsInterval=10,
        highTrafficAvgThreshold=10,
        highTrafficInterval=120,
    ):
        super().__init__(action)
        # Initialize calculators, each with its own time-window size
        cls._statsCalculators = [
            MostCommonCalculator(action, mostCommonStatsInterval),
            HighTrafficCalculator(action, highTrafficInterval, highTrafficAvgThreshold),
        ]
        # Cache max sliding window size
        cls._widestWindowSize = max(
            [calc.getWindowSize() for calc in cls._statsCalculators]
        )
        # Collect events in a SortedList due to out-of-order possibility.
        cls._events: Any = SortedList()

    def consume(cls, newestEvent: WebEvent) -> None:  # type: ignore[override]
        """Consume sourced traffic entry, calculate stats and volume changes in traffic"""

        cls._events.add(newestEvent)

        # Remove all entries that fall out from start of the widest window interval,
        # updating calculations along the way
        cls._removeOldEvents(newestEvent)

        # Add new event to calculations
        for calc in cls._statsCalculators:
            calc.count(newestEvent)

    def _removeOldEvents(cls, newestEvent: WebEvent) -> None:
        "Remove one or more events that have fallen out of any calculators' time-intervals"

        # Remove from collected list of events
        while newestEvent.time - cls._events[0].time > cls._widestWindowSize:
            outdatedEvent = cls._events.pop(0)
            logging.debug(f"Removed outdated event {outdatedEvent.time}.")
            for calc in cls._statsCalculators:
                calc.discount(outdatedEvent, newestEvent)

        # Starting from oldest event, let each calculator remove from its calculations any
        # events that have fallen outside window intervals, given the newest one
        for e in cls._events:
            isRemovedFromCalculation = False
            for calc in cls._statsCalculators:
                if calc.discount(e, newestEvent):
                    isRemovedFromCalculation = True

            # Keep attempting until event is discounted from every calculator's window
            if not isRemovedFromCalculation:
                break


class WindowedCalculator:
    "Interface for implementing different kinds of statistics calculation on a window of events"

    def __init__(cls, action: Action, windowSizeInSeconds=10):
        # Time window required for calculations
        cls._WINDOW_SIZE_DELTA = datetime.timedelta(seconds=windowSizeInSeconds)

        # To trigger any alerts if needed
        cls._action = action

        # Start time of sliding window specific to this calculator
        # Window could be smaller than the main window of collected events
        # Window is any time after this, i.e.:
        #   _windowStartsAfterEvent.time < newestEvent - _WINDOW_SIZE_DELTA <= newestEvent
        cls._windowStartsAfterEvent: Optional[WebEvent] = None

    def getWindowSize(cls) -> datetime.timedelta:
        "Size of time window this calculator requires to function"
        return cls._WINDOW_SIZE_DELTA

    def _isWithinWindow(cls, oldEvent: WebEvent, newestEvent: WebEvent) -> bool:
        "Check if given event falls within window interval relative to the newest event"
        return (
            # Ensure window is positive, in case it's deactivated
            cls._WINDOW_SIZE_DELTA > datetime.timedelta(0)
            # And time difference within the window size
            and newestEvent.time - oldEvent.time <= cls._WINDOW_SIZE_DELTA
        ) and (
            cls._windowStartsAfterEvent is None
            # TODO this used to be <=
            or (
                oldEvent.time > cls._windowStartsAfterEvent.time
                and oldEvent != cls._windowStartsAfterEvent
            )
        )

    def discount(cls, e: WebEvent, newestEvent) -> bool:
        "Check event as it may or may not the sliding window, return true if it did"
        if cls._isWithinWindow(oldEvent=e, newestEvent=newestEvent):
            cls._removeFromCalculation(e)
            cls._windowStartsAfterEvent = e
            return True
        # We didn't delete anything as it was outside the window anyway
        return False

    def count(cls, event: WebEvent) -> None:
        "Consume an event as it enters in the sliding window interval"
        raise NotImplementedError()

    def _removeFromCalculation(cls, event: WebEvent) -> None:
        "Implement to perform the actual removal from overall calculation of out of window event"
        raise NotImplementedError()

    def _triggerAlert(cls, event: WebEvent) -> None:
        "Implement to check if conditions are met for sending any alerting"
        raise NotImplementedError()


class HighTrafficCalculator(WindowedCalculator):
    "Trigger alert if average traffic crosses the given threshold or returns back to normal"

    def __init__(
        cls, action: Action, windowSizeInSeconds=120, highTrafficAvgThreshold=10
    ):
        super().__init__(action, windowSizeInSeconds)

        cls._highTrafficAvgThreshold: int = highTrafficAvgThreshold
        cls._highTrafficAlertMode = False
        cls._highTrafficTotalCount: int = 0

    def count(cls, e: WebEvent) -> None:
        "Count to use in high traffic average"
        cls._highTrafficTotalCount += 1
        cls._triggerAlert(e)

    def _removeFromCalculation(cls, e: WebEvent) -> None:
        cls._highTrafficTotalCount -= 1
        cls._triggerAlert(e)

    def _triggerAlert(cls, latestEvent: WebEvent) -> None:

        if cls.getWindowSize() < datetime.timedelta(0):
            # Negative interval, skip check
            logging.debug("High traffic checks deactivated")
            return

        now = latestEvent.time

        timeInterval = cls._WINDOW_SIZE_DELTA.total_seconds()
        # average = int(cls._highTrafficTotalCount / max(1, timeInterval))
        average = cls._highTrafficTotalCount

        logging.debug(f"High traffic average: {average}")
        # Fire only if average exceeds threshold
        if average > cls._highTrafficAvgThreshold and not cls._highTrafficAlertMode:
            alertHighTraffic: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message="High traffic generated an alert - "
                f"hits {average}, triggered at {now}",
            )
            cls._action.notify(alertHighTraffic)
            cls._highTrafficAlertMode = True
            logging.debug(f"High traffic, fired {alertHighTraffic}")

        # If back to normal again, alert only once
        if average <= cls._highTrafficAvgThreshold and cls._highTrafficAlertMode:
            alertBackToNormal: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message=f"Traffic is now back to normal as of {now}",
            )
            cls._action.notify(alertBackToNormal)
            cls._highTrafficAlertMode = False
            logging.debug(f"High traffic back to normal, fired {alertBackToNormal}")


class MostCommonCalculator(WindowedCalculator):
    "Keeps track of most common source, most common section in a given time-interval"

    def __init__(cls, action: Action, windowSizeInSeconds=10):
        super().__init__(action, windowSizeInSeconds)

        # Used for counting "most common" traffic stats
        cls._timeLastCollectedStats: Optional[datetime.datetime] = None
        cls._countSections: Counter[str] = Counter()
        cls._countSources: Counter[str] = Counter()

    def _removeFromCalculation(cls, e: WebEvent) -> None:
        logging.debug(f"Removing old event from most common stats: {e.time}")
        cls._countSections[e.section] -= 1
        cls._countSources[e.source] -= 1
        # No need to update calculation for this calculator at 'discount'
        # Alerts can only be generated when we add a new one

    def count(cls, e: WebEvent) -> None:
        logging.debug(f"Counting log {e.section} from {e.source} at {e.time}")
        cls._countSections[e.section] += 1
        cls._countSources[e.source] += 1
        cls._triggerAlert(e)

    def _triggerAlert(cls, latestEvent: WebEvent) -> None:
        """ Refresh calculation, trigger alerts with most common sections/sources when applicable """

        if cls.getWindowSize() < datetime.timedelta(0):
            # Negative interval -> Stats calculation are deactivated
            return

        cls._timeLastCollectedStats = cls._timeLastCollectedStats or latestEvent.time
        if (latestEvent.time - cls._timeLastCollectedStats) < cls.getWindowSize():
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
        logging.debug(f"Fired stats {statsEvent}")
        cls._action.notify(statsEvent)
        cls._timeLastCollectedStats = latestEvent.time