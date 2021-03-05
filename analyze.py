import os
import event
import typing
import logging
import datetime
from action import Action
from collections import deque, Counter


class Processor:
    """ Collect and anlyzes parsed log entries, and infer higher-level events """

    def __init__(cls, action: Action):
        cls.action = action
        cls.events: typing.Deque(event.Event) = deque()
        cls.statsInterval = datetime.timedelta(
            seconds=os.getenv("DD_STATS_INTERVAL_SECONDS", 10)
        )

    def consume(cls, event: event.Event) -> None:
        """ Consume log event and generate other events if applicable """
        raise NotImplementedError()


class HTTPEventProcessor(Processor):
    """ Anlyzes parsed HTTP events """

    def __init__(cls, action: Action):
        super().__init__(action)
        logging.basicConfig(level=logging.INFO)
        cls.log = logging.getLogger(__name__)
        # Used for general traffic stats
        cls.timeLastCollectedStats = None

    def consume(cls, eventParsed: event.HTTPEvent) -> None:
        """ Consume HTTP log entry, calculate stats and traffic volume changes """
        cls.events.append(eventParsed)
        cls._calculateStats(eventParsed)
        cls._checkSurgesAndDrops(eventParsed)

    def _calculateStats(cls, latestEvent: event.HTTPEvent) -> None:
        """ General stats """
        cls.timeLastCollectedStats = cls.timeLastCollectedStats or latestEvent.time
        if (latestEvent.time - cls.timeLastCollectedStats) < cls.statsInterval:
            # Latest event time hasn't yet crossed interval
            return
        countSections = Counter()
        countSources = Counter()
        # Start from most recent event and stop when window interval reached
        for e in reversed(cls.events):
            # Skip old events outside interval for stats calculation
            if (latestEvent.time - e.time) > (cls.statsInterval):
                cls.log.debug("Skipping old events starting from %s" % e.time)
                break
            countSections[e.section] += 1
            countSources[e.source] += 1
            trafficEvent = event.Event(
                priority=event.Event.Priority.MEDIUM,
                message="Stats - highest freq sections "
                + str(countSections.most_common(1)[0])
                + ", sources: "
                + str(countSources.most_common(1)[0]),
                time=latestEvent.time,
            )
        cls.action.notify(trafficEvent)
        cls.timeLastCollectedStats = latestEvent.time

    def _checkSurgesAndDrops(cls, eventParsed: event.HTTPEvent) -> None:
        # TODO Discard items when they fall out of the widest time window
        # cls.events.popleft()
        pass
