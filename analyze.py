import logging
import datetime
from os import getenv
from event import Event, WebEvent
from action import Action
from typing import Counter, Optional
from collections import Counter
from sortedcontainers import SortedList


class Processor:
    """ Collect and analyzes parsed log entries, and infer higher-level events """

    def __init__(cls, action: Action):
        cls._action = action

    def consume(cls, event: Event) -> None:
        """ Consume log event and generate other events if applicable """
        raise NotImplementedError()


class StatsProcessor(Processor):
    """ Analyzes sourced traffic events """

    def __init__(
        cls,
        action: Action,
        statsInterval=10,
        highTrafficAvgThreshold=10,
        highTrafficInterval=120,
    ):
        super().__init__(action)
        cls._log = logging.getLogger(__name__)

        # Collect events in a SortedList due to out-of-order possibility.
        #  O(n*log(n)), otherwise O(n) with a deque() instead.
        # (SortedList read/remove/insert are O(log(n)) each)
        cls._events: list[WebEvent] = SortedList()
        cls._statsInterval = datetime.timedelta(seconds=statsInterval)
        cls._statsOldestEventDiscounted: Optional[WebEvent] = None

        # Used for general traffic stats
        cls._timeLastCollectedStats: Optional[datetime.datetime] = None
        cls._countSections: Counter[str] = Counter()
        cls._countSources: Counter[str] = Counter()

        # Used for high traffic alerts
        cls._highTrafficInterval = datetime.timedelta(seconds=highTrafficInterval)
        cls._highTrafficAvgThreshold = highTrafficAvgThreshold
        cls._highTrafficAlertMode = False
        cls._highTrafficOldestEventDiscounted: Optional[WebEvent] = None
        cls._highTrafficTotalCount: int = 0

    def _discountEvent(cls, e: WebEvent) -> bool:
        """
        Discounts event from all calculations,
        returns true if at least one calculation type  removed it
        """

        isDiscounted = False
        timeTillNow = cls._events[-1].time - e.time
        # Remove events that are now outside interval for stats calculation
        # Cache and stop at previously removed event so we don't discount it multiple times.
        if (
            cls._statsInterval > datetime.timedelta(0)  # In case it's deactivated
            and timeTillNow > cls._statsInterval
        ) and (
            cls._statsOldestEventDiscounted is None
            or (
                e.time <= cls._statsOldestEventDiscounted.time
                and e != cls._highTrafficOldestEventDiscounted
            )
        ):
            cls._log.debug(f"Removing old event from most common stats: {e.time}")
            cls._countSections[e.section] -= 1
            cls._countSources[e.source] -= 1

            # Only set the window start if it has been reset
            # due to reaching it, otherwise we'd overrite with an earlier time
            if (
                not cls._statsOldestEventDiscounted
                or cls._statsOldestEventDiscounted.time < e.time
            ):
                cls._statsOldestEventDiscounted = e
            isDiscounted = True

        # Discount from high traffic stats if applicable
        # Cache and stop at previously removed event so we don't discount it multiple times.
        if (
            cls._highTrafficInterval > datetime.timedelta(0)  # In case it's deactivated
            and timeTillNow > cls._highTrafficInterval
        ) and (
            cls._highTrafficOldestEventDiscounted is None
            or (
                e.time <= cls._highTrafficOldestEventDiscounted.time
                and e != cls._highTrafficOldestEventDiscounted
            )
        ):
            cls._log.debug(f"Removing event outside High Traffic window: {e.time}")
            cls._highTrafficTotalCount -= 1
            isDiscounted = True
            if (
                not cls._highTrafficOldestEventDiscounted
                or cls._highTrafficOldestEventDiscounted.time < e.time
            ):
                cls._highTrafficOldestEventDiscounted = e

        return isDiscounted

    def _removeAndDiscountOldestEvents(cls) -> None:
        # Start from oldest event and remove those that have gone outside widest interval
        outdatedEvent = cls._events.pop(0)

        # Invalidate cached left window if it is reached
        if (
            cls._statsOldestEventDiscounted
            and outdatedEvent.time >= cls._statsOldestEventDiscounted.time
        ):
            cls._statsOldestEventDiscounted = None

        if (
            cls._highTrafficOldestEventDiscounted
            and outdatedEvent.time >= cls._highTrafficOldestEventDiscounted.time
        ):
            cls._highTrafficOldestEventDiscounted = None

        cls._discountEvent(outdatedEvent)
        cls._log.debug(f"Removed outdated event {outdatedEvent.time}.")

    def _countNewEvent(cls, e: WebEvent) -> None:
        cls._log.debug(f"Counting log {e.section} from {e.source} at {e.time}")
        cls._countSections[e.section] += 1
        cls._countSources[e.source] += 1

        # Count to use in high traffic average
        cls._highTrafficTotalCount += 1

    def consume(cls, webEvent: WebEvent) -> None:  # type: ignore[override]
        """ Consume sourced traffic entry, calculate stats and volume changes in traffic """
        cls._events.add(webEvent)

        widestWindowStart = webEvent.time - max(
            cls._statsInterval, cls._highTrafficInterval
        )
        # Remove all entries that fall out of widest window intervals
        while cls._events[0].time < widestWindowStart:
            cls._removeAndDiscountOldestEvents()

        # Also update calculations for entries in smaller window intervals
        # without removing any more events
        for e in cls._events:
            if not cls._discountEvent(e):
                break
        # Add new event to calculation and list of events
        cls._countNewEvent(webEvent)

        cls._calculateStats(webEvent)
        cls._highTrafficChecks(webEvent)

    def _calculateStats(cls, latestEvent: WebEvent) -> None:
        """ General stats """

        if cls._statsInterval < datetime.timedelta(0):
            # Negative interval -> Stats calculation are deactivated
            return

        cls._timeLastCollectedStats = cls._timeLastCollectedStats or latestEvent.time
        if (latestEvent.time - cls._timeLastCollectedStats) < cls._statsInterval:
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
        cls._log.debug(f"Fired stats {statsEvent}")
        cls._action.notify(statsEvent)
        cls._timeLastCollectedStats = latestEvent.time

    def _highTrafficChecks(cls, webEvent: WebEvent) -> None:

        if cls._highTrafficInterval < datetime.timedelta(0):
            # Negative interval, skip check
            cls._log.debug("High traffic checks deactivated")
            return

        now = webEvent.time
        average = cls._highTrafficTotalCount

        cls._log.debug(f"High traffic average: {average}")
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
            cls._log.debug(f"High traffic, fired {alertHighTraffic}")

        # If back to normal again, alert only once
        if average <= cls._highTrafficAvgThreshold and cls._highTrafficAlertMode:
            alertBackToNormal: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message=f"Traffic is now back to normal as of {now}",
            )
            cls._action.notify(alertBackToNormal)
            cls._highTrafficAlertMode = False
            cls._log.debug(f"High traffic back to normal, fired {alertBackToNormal}")
