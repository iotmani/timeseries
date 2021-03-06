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

    def __init__(cls, action: Action):
        super().__init__(action)
        cls.log = logging.getLogger(__name__)

        cls.events: Deque[WebEvent] = deque()
        cls.statsInterval = datetime.timedelta(
            seconds=int(getenv("DD_STATS_INTERVAL_SECONDS", 10))
        )
        # Used for general traffic stats
        cls.timeLastCollectedStats: Optional[datetime.datetime] = None

    def consume(cls, eventParsed: WebEvent) -> None:  # type: ignore[override]
        """ Consume sourced traffic entry, calculate stats and volume changes in traffic """
        cls.events.append(eventParsed)
        cls._calculateStats(eventParsed)
        cls._checkSurgesAndDrops(eventParsed)

    def _calculateStats(cls, latestEvent: WebEvent) -> None:
        """ General stats """
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
                cls.log.debug(
                    f"Skipping old events starting from {e.time}"
                    f"(interval {latestEvent.time - e.time})"
                )
                break
            cls.log.debug(f"counting log {e.section} from {e.source} at {e.time}")
            countSections[e.section] += 1
            countSources[e.source] += 1
        trafficEvent = Event(
            priority=Event.Priority.MEDIUM,
            message="Stats - Highest freq sections "
            + str(countSections.most_common(1)[0])
            + ", sources: "
            + str(countSources.most_common(1)[0]),
            time=latestEvent.time,
        )
        cls.log.debug(trafficEvent)
        cls.action.notify(trafficEvent)
        cls.timeLastCollectedStats = latestEvent.time

    def _checkSurgesAndDrops(cls, eventParsed: WebEvent) -> None:
        # TODO Discard items when they fall out of the widest time window
        # cls.events.popleft()
        pass
