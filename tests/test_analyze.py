import unittest
from event import HTTPEvent, Event
from action import Action
from analyze import HTTPEventProcessor, Processor
from datetime import datetime, timedelta
from collections import deque
from unittest.mock import MagicMock


class TestAnalyzeAlgorithms(unittest.TestCase):
    def _constructEvent(cls, time):
        """ Construct commonly required Event content where only time matters """
        return HTTPEvent(
            time=time,
            priority=HTTPEvent.Priority.MEDIUM,
            message="Some log",
            rfc931=None,
            authuser=None,
            status=None,
            size=None,
            section="/api",
            source="GCHQ",
            request=None,
        )

    def testCalculateStats(cls):
        """Test that we generate stats only when expected,
        and with only the relevant events"""

        action = MagicMock()
        proc = HTTPEventProcessor(action)
        now = datetime.now()
        cls.statsInterval = timedelta(seconds=10)

        e1 = cls._constructEvent(now - timedelta(minutes=30))
        proc.consume(e1)
        cls.assertEqual(
            now - timedelta(minutes=30),
            proc.timeLastCollectedStats,
            "Time last collected stats must equal first and only event's time",
        )
        cls.assertEqual(
            0,
            action.notify.call_count,
            "No notification generated from first ever event",
        )

        timeWithinInterval = now - timedelta(seconds=20)
        e2Recent = cls._constructEvent(timeWithinInterval)
        e2Recent.time = timeWithinInterval
        e2Recent.section = "/api"
        e2Recent.source = "NSA"
        proc.consume(e2Recent)

        action1Expected = Event(
            priority=Event.Priority.MEDIUM,
            message="Stats - highest freq sections "
            + str((e2Recent.section, 1))
            + ", sources: "
            + str((e2Recent.source, 1)),
            time=timeWithinInterval,
        )
        action.notify.assert_called_with(action1Expected)

        cls.assertEqual(
            proc.timeLastCollectedStats,
            e2Recent.time,
            "Time last collected status must equal latest event",
        )

        cls.assertEqual(2, len(proc.events))
        e3TooRecent = cls._constructEvent(now - timedelta(seconds=15))
        proc.consume(e3TooRecent)
        cls.assertEqual(3, len(proc.events))
        action.notify.assert_called_once()

        e4StillTooRecent = cls._constructEvent(now - timedelta(seconds=11))
        proc.consume(e4StillTooRecent)
        cls.assertEqual(
            4, len(proc.events), "Expecting exactly this many log events collected"
        )
        action.notify.assert_called_once()

        e5NewIntervalCrossed = cls._constructEvent(now - timedelta(seconds=10))
        proc.consume(e5NewIntervalCrossed)
        cls.assertEqual(5, len(proc.events))

        action2Expected = Event(
            priority=Event.Priority.MEDIUM,
            message="Stats - highest freq sections "
            + str((e5NewIntervalCrossed.section, 4))
            + ", sources: "
            + str((e5NewIntervalCrossed.source, 3)),
            time=now - timedelta(seconds=10),
        )
        # Expected new frequency event to be generated
        # Expected to only count new events since last generated, no overlapping points
        action.notify.assert_called_with(action2Expected)

        # Within new interval, shouldn't trigger another event
        e6within = cls._constructEvent(now - timedelta(seconds=4))
        proc.consume(e6within)

        cls.assertEqual(
            6, len(proc.events), "Expecting exactly this many log events collected"
        )

        cls.assertEqual(
            2, action.notify.call_count, "No more events should be generated"
        )

    def testProcessorNotImplemented(cls):
        # Just for better code coverage
        with cls.assertRaises(NotImplementedError):
            e = cls._constructEvent("2021-03-05")
            Processor(Action()).consume(e)