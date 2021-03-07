import unittest
from event import WebEvent, Event
from action import Action
from analyze import StatsProcessor, Processor
from datetime import datetime, timedelta
from collections import deque
from unittest.mock import MagicMock


class TestAnalyzeAlgorithms(unittest.TestCase):
    "Test analyze module functions"

    def _makeEvent(cls, time):
        """ Construct commonly required Event content where only time matters """
        return WebEvent(
            time=time,
            priority=WebEvent.Priority.MEDIUM,
            message="Some log",
            rfc931=None,
            authuser=None,
            status=None,
            size=None,
            section="/api",
            source="GCHQ",
            request=None,
        )

    def testHighTrafficCheck(cls):
        """ Test high traffic and back to normal alerting """

        action = MagicMock()
        proc = StatsProcessor(action)
        # Fix now to an easier to reason about
        now = datetime.strptime("2020-01-01 00:00:00.000000", "%Y-%m-%d %H:%M:%S.%f")

        # Deactivate other stats calculation to only focus on High Traffic
        proc.statsInterval = timedelta(-1)

        # I.e. calculate average over past 2 mins
        proc.highTrafficInterval = timedelta(seconds=120)
        # Set High Traffic threshold to x messages during the interval
        proc.highTrafficAvgThreshold = 3

        # From normal to High traffic
        e0 = cls._makeEvent(now + timedelta(minutes=0))
        e1 = cls._makeEvent(now + timedelta(minutes=1))
        e2 = cls._makeEvent(now + timedelta(minutes=2))
        e3 = cls._makeEvent(now + timedelta(minutes=3))
        e4 = cls._makeEvent(now + timedelta(minutes=3))
        e5 = cls._makeEvent(now + timedelta(minutes=4))
        proc.consume(e0)
        proc.consume(e1)
        proc.consume(e2)
        cls.assertEqual(3, len(proc.events), "All events collected")
        proc.consume(e3)
        cls.assertEqual(3, len(proc.events), "First event is outside window")
        # Ensure no high traffic alerts were fired
        cls.assertEqual(0, action.notify.call_count, "Did not reach threshold")

        proc.consume(e4)
        # Check High alert fired
        alertHighTraffic = Event(
            time=e4.time,
            priority=Event.Priority.HIGH,
            message="High traffic generated an alert - "
            f"hits 4, triggered at {e4.time}",
        )
        action.notify.assert_called_with(alertHighTraffic)

        # Only generate alert once if we continue to cross threshold
        proc.consume(e5)
        action.notify.assert_called_once()
        cls.assertEqual(4, len(proc.events), "First two events are now outside window")

        # Back to normal also generates alert
        e6 = cls._makeEvent(now + timedelta(minutes=6))
        proc.consume(e6)
        alertBackToNormal = Event(
            time=e6.time,
            priority=Event.Priority.HIGH,
            message=f"Traffic is now back to normal as of {e6.time}",
        )
        action.notify.assert_called_with(alertBackToNormal)

        e7 = cls._makeEvent(now + timedelta(minutes=9))
        proc.consume(e7)
        cls.assertEqual(
            2, action.notify.call_count, "No more alerts as traffic stays low"
        )
        cls.assertEqual(1, len(proc.events), "Only one event collected")

        # Traffic up, alert High again
        e8 = cls._makeEvent(now + timedelta(minutes=9))
        e9 = cls._makeEvent(now + timedelta(minutes=9))
        e10 = cls._makeEvent(now + timedelta(minutes=9))
        proc.consume(e8)
        proc.consume(e9)
        proc.consume(e10)
        alertHighTraffic = Event(
            time=e10.time,
            priority=Event.Priority.HIGH,
            message="High traffic generated an alert - "
            f"hits 4, triggered at {e10.time}",
        )
        action.notify.assert_called_with(alertHighTraffic)

    def testCalculateStats(cls):
        """Test that we generate stats only when expected,
        and with only the relevant events"""

        action = MagicMock()
        proc = StatsProcessor(action)
        # Set now time to an easier to reason about
        now = datetime.strptime("2020-01-01 00:00:00.000000", "%Y-%m-%d %H:%M:%S.%f")

        proc.statsInterval = timedelta(seconds=10)
        proc.highTrafficInterval = timedelta(-1)  # Deactivate

        e1 = cls._makeEvent(now - timedelta(minutes=30))
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
        e2Recent = cls._makeEvent(timeWithinInterval)
        e2Recent.time = timeWithinInterval
        e2Recent.section = "/api"
        e2Recent.source = "NSA"
        proc.consume(e2Recent)

        action1Expected = Event(
            priority=Event.Priority.MEDIUM,
            message="Most common section: "
            + f"{e2Recent.section} (1 requests)"
            + ", source: "
            + f"{e2Recent.source} (1 requests)",
            time=timeWithinInterval,
        )

        action.notify.assert_called_with(action1Expected)

        cls.assertEqual(
            proc.timeLastCollectedStats,
            e2Recent.time,
            "Time last collected status must equal latest event",
        )

        cls.assertEqual(1, len(proc.events), "Only one kept within time interval")
        e3TooRecent = cls._makeEvent(now - timedelta(seconds=15))
        proc.consume(e3TooRecent)
        cls.assertEqual(2, len(proc.events))
        action.notify.assert_called_once()

        e4StillTooRecent = cls._makeEvent(now - timedelta(seconds=11))
        proc.consume(e4StillTooRecent)
        cls.assertEqual(
            3, len(proc.events), "Expecting exactly this many log events collected"
        )
        action.notify.assert_called_once()

        e5NewIntervalCrossed = cls._makeEvent(now - timedelta(seconds=10))
        proc.consume(e5NewIntervalCrossed)
        cls.assertEqual(4, len(proc.events))

        action2Expected = Event(
            priority=Event.Priority.MEDIUM,
            message="Most common section: "
            + f"{e5NewIntervalCrossed.section} (4 requests)"
            + ", source: "
            + f"{e5NewIntervalCrossed.source} (3 requests)",
            time=now - timedelta(seconds=10),
        )
        # Expected new frequency event to be generated
        # Expected to only count new events since last generated, no overlapping points
        action.notify.assert_called_with(action2Expected)

        # Within new interval, shouldn't trigger another event
        e6within = cls._makeEvent(now - timedelta(seconds=4))
        proc.consume(e6within)

        cls.assertEqual(
            3, len(proc.events), "Expecting exactly this many log events collected"
        )

        cls.assertEqual(
            2, action.notify.call_count, "No more events should be generated"
        )

    def testHighTrafficAndStatsTogether(cls):
        """Ensure no unenxpected interference when running both,
        and with different interval windows.
        """

        action = MagicMock()
        proc = StatsProcessor(
            action, statsInterval=120, highTrafficInterval=60, highTrafficAvgThreshold=1
        )

        # Consume a bunch of web events
        now = datetime.strptime("2020-01-01 00:00:00.000000", "%Y-%m-%d %H:%M:%S.%f")
        events = [
            cls._makeEvent(now + timedelta(minutes=0)),
            cls._makeEvent(now + timedelta(minutes=1)),
            cls._makeEvent(now + timedelta(minutes=2)),
            cls._makeEvent(now + timedelta(minutes=3)),
            cls._makeEvent(now + timedelta(minutes=3)),
            cls._makeEvent(now + timedelta(minutes=4)),
            cls._makeEvent(now + timedelta(minutes=7)),
        ]
        for e in events:
            proc.consume(e)

        cls.assertEqual(
            5,
            action.notify.call_count,
            "Expected this many stats and high traffic alerts",
        )

    def testProcessorNotImplemented(cls):
        " Just for better code coverage "
        with cls.assertRaises(NotImplementedError):
            e = cls._makeEvent("2021-03-05")
            Processor(Action()).consume(e)