import unittest
from event import HTTPEvent, Event
from action import Action
from datetime import datetime, timedelta
from analyze import HTTPEventProcessor

from collections import deque
from unittest.mock import MagicMock


class TestAnalyzeAlgorithms(unittest.TestCase):
    def testCalculateStats(cls):
        action = MagicMock()
        proc = HTTPEventProcessor(action)

        now = datetime.now()
        timeThirtyMinutesAgo = now - timedelta(minutes=30)
        e1 = HTTPEvent(
            time=timeThirtyMinutesAgo,
            priority=HTTPEvent.Priority.MEDIUM,
            message="Some log",
            rfc931=None,
            authuser=None,
            status=None,
            size=None,
            section="/api",
            source=None,
            request=None,
        )
        proc.consume(e1)

        cls.assertEqual(
            timeThirtyMinutesAgo,
            proc.timeLastCollectedStats,
            "Time last collected stats must equal first and only event's time",
        )

        timeWithinInterval = now - timedelta(seconds=8)
        e2Recent = HTTPEvent(
            time=timeWithinInterval,
            priority=HTTPEvent.Priority.MEDIUM,
            message="Some other log",
            rfc931=None,
            authuser=None,
            status=None,
            size=None,
            section="/api",
            source="NSA",
            request=None,
        )
        proc.consume(e2Recent)

        actionEvent1Generated = Event(
            priority=Event.Priority.MEDIUM,
            message="Stats - highest freq sections "
            + str((e2Recent.section, 1))
            + ", sources: "
            + str((e2Recent.source, 1)),
            time=timeWithinInterval,
        )
        action.notify.assert_called_with(actionEvent1Generated)

        cls.assertEqual(
            proc.timeLastCollectedStats,
            e2Recent.time,
            "Time last collected status must equal latest event",
        )

        cls.assertEqual(2, len(proc.events))
        e3TooRecent = HTTPEvent(
            time=now - timedelta(seconds=5),
            priority=HTTPEvent.Priority.MEDIUM,
            message="yet another log",
            rfc931=None,
            authuser=None,
            status=None,
            size=None,
            section="/api",
            source="GCHQ",
            request=None,
        )
        proc.consume(e3TooRecent)
        cls.assertEqual(3, len(proc.events))
        action.notify.assert_called_once()

        e4StillTooRecent = e3TooRecent
        e4StillTooRecent.time = now - timedelta(seconds=2)
        proc.consume(e4StillTooRecent)
        cls.assertEqual(4, len(proc.events))
        action.notify.assert_called_once()

        e5NewIntervalCrossed = e3TooRecent
        e5NewIntervalCrossed.time = now + timedelta(seconds=2)
        proc.consume(e5NewIntervalCrossed)
        cls.assertEqual(5, len(proc.events))
