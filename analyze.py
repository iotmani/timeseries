import logging
import datetime
from os import getenv
from event import Event, WebEvent
from action import Action
from typing import Deque, Counter, Optional
from collections import deque, Counter


class Processor:
    """ Collect and analyzes parsed log entries, and infer higher-level events """

    def __init__(cls, action: Action):
        cls.action = action

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
        cls.log = logging.getLogger(__name__)

        cls.events: Deque[WebEvent] = deque()
        cls.statsInterval = datetime.timedelta(seconds=statsInterval)
        # Used for general traffic stats
        cls.timeLastCollectedStats: Optional[datetime.datetime] = None

        # Used for high traffic alerts
        cls.highTrafficInterval = datetime.timedelta(seconds=highTrafficInterval)
        cls.highTrafficAvgThreshold = highTrafficAvgThreshold
        cls.highTrafficAverage: Optional[int] = None
        cls.highTrafficAlertMode = False

    def consume(cls, webEvent: WebEvent) -> None:  # type: ignore[override]
        """ Consume sourced traffic entry, calculate stats and volume changes in traffic """

        cls.events.append(webEvent)

        # Remove elements outside maximum interval, if any
        windowStart = webEvent.time - max(cls.statsInterval, cls.highTrafficInterval)
        while True:
            # Don't delete and iterate over deque with invalidated iterators, but there's probably a better way
            if cls.events[0].time < windowStart:
                outdatedEvent = cls.events.popleft()
                cls.log.debug(f"Removed outdated event {outdatedEvent.time}.")
            else:
                # Stop at first one within since they're sorted by occurrence time
                break

        cls._calculateStats(webEvent)
        cls._highTrafficChecks(webEvent)

    def _calculateStats(cls, latestEvent: WebEvent) -> None:
        """ General stats """

        if cls.statsInterval < datetime.timedelta(0):
            # Negative interval -> Stats calculation are deactivated
            return

        cls.timeLastCollectedStats = cls.timeLastCollectedStats or latestEvent.time
        if (latestEvent.time - cls.timeLastCollectedStats) < cls.statsInterval:
            # Latest event time hasn't yet crossed the full interval
            return

        countSections: Counter[str] = Counter()
        countSources: Counter[str] = Counter()
        # Start from most recent event and up, stop when window interval reached
        e: WebEvent
        for e in reversed(cls.events):
            # Skip old events outside interval for stats calculation
            if (latestEvent.time - e.time) > (cls.statsInterval):
                cls.log.debug(f"Skipping old events starting from {e.time}")
                break
            cls.log.debug(f"Counting log {e.section} from {e.source} at {e.time}")
            countSections[e.section] += 1
            countSources[e.source] += 1
        mostCommonSection = countSections.most_common(1)[0]
        mostCommonSource = countSources.most_common(1)[0]
        statsEvent = Event(
            priority=Event.Priority.MEDIUM,
            message="Most common section: "
            + f"{mostCommonSection[0]} ({mostCommonSection[1]} requests)"
            + ", source: "
            + f"{mostCommonSource[0]} ({mostCommonSource[1]} requests)",
            time=latestEvent.time,
        )
        cls.log.debug(f"Fired stats {statsEvent}")
        cls.action.notify(statsEvent)
        cls.timeLastCollectedStats = latestEvent.time

    def _highTrafficChecks(cls, webEvent: WebEvent) -> None:

        if cls.highTrafficInterval < datetime.timedelta(0):
            # Negative interval, skip check
            cls.log.debug("High traffic checks deactivated")
            return

        now = webEvent.time

        # Iterate till start of window in case interval isn't the biggest
        # TODO calculate average efficiently
        # average = len(cls.events)
        average = 0
        e: WebEvent
        for e in iter(cls.events):
            if (now - e.time) > cls.highTrafficInterval:
                cls.log.debug(f"Skipping event outside High Traffic window: {e.time}")
            else:
                average += 1

        cls.log.debug(f"High traffic average: {average}")
        # Fire only if average exceeds threshold
        if average > cls.highTrafficAvgThreshold and not cls.highTrafficAlertMode:
            alertHighTraffic: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message="High traffic generated an alert - "
                f"hits {average}, triggered at {now}",
            )
            cls.action.notify(alertHighTraffic)
            cls.highTrafficAlertMode = True
            cls.log.debug(f"High traffic, fired {alertHighTraffic}")

        # If back to normal again, alert only once
        if average <= cls.highTrafficAvgThreshold and cls.highTrafficAlertMode:
            alertBackToNormal: Event = Event(
                time=now,
                priority=Event.Priority.HIGH,
                message=f"Traffic is now back to normal as of {now}",
            )
            cls.action.notify(alertBackToNormal)
            cls.highTrafficAlertMode = False
            cls.log.debug(f"High traffic back to normal, fired {alertBackToNormal}")
