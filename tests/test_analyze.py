import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from LogsMonitor2000.event import WebEvent, Event
from LogsMonitor2000.action import Action
from LogsMonitor2000.analyze import StatsProcessor, Processor
from LogsMonitor2000.analyze.calculator import WindowedCalculator, MostCommonCalculator


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

    def testHighTrafficAlerts(cls):
        """ Test high traffic and back to normal alerting """

        action = MagicMock()
        # Deactivate other stats calculation to only focus on High Traffic
        # And calculate average over past 2 mins
        # Set High Traffic threshold to x messages during the interval
        proc = StatsProcessor(
            action,
            mostCommonStatsInterval=-1,
            highTrafficInterval=120,
            highTrafficAvgThreshold=3,
        )

        # Fix now to an easier to reason about
        now = datetime.strptime("2020-01-01 00:00:00.000000", "%Y-%m-%d %H:%M:%S.%f")

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
        cls.assertEqual(3, len(proc._events), "All events collected")
        proc.consume(e3)
        cls.assertEqual(3, len(proc._events), "First event is outside window")
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
        cls.assertEqual(4, len(proc._events), "First two events are now outside window")

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
        cls.assertEqual(1, len(proc._events), "Only one event collected")

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

    def testMostCommonStats(cls):
        """Test that we generate stats only when expected,
        and with only the relevant events"""

        action = MagicMock()
        # Deactivate high traffic calculation
        proc = StatsProcessor(
            action, mostCommonStatsInterval=10, highTrafficInterval=-1
        )
        # Set now time so we add logs relative to that
        now = datetime.strptime("2020-01-01 00:00:00.000000", "%Y-%m-%d %H:%M:%S.%f")

        e0 = cls._makeEvent(now + timedelta(minutes=0))
        e1 = cls._makeEvent(now + timedelta(minutes=30, seconds=0))
        e2 = cls._makeEvent(now + timedelta(minutes=30, seconds=5))
        e3 = cls._makeEvent(now + timedelta(minutes=30, seconds=9))
        e4 = cls._makeEvent(now + timedelta(minutes=30, seconds=10))
        e5 = cls._makeEvent(now + timedelta(minutes=30, seconds=14))
        e6 = cls._makeEvent(now + timedelta(minutes=30, seconds=58))

        proc.consume(e0)
        cls.assertEqual(
            e0.time,
            proc._statsCalculators[0]._timeLastCollectedStats,
            "Time last collected stats must equal first and only event's time",
        )
        cls.assertEqual(
            0,
            action.notify.call_count,
            "No notification generated from first ever event",
        )

        e1.section = "/api"
        e1.source = "NSA"
        proc.consume(e1)

        alert1 = Event(
            priority=Event.Priority.MEDIUM,
            message="Most common section: "
            + f"{e1.section} (1 requests)"
            + ", source: "
            + f"{e1.source} (1 requests)",
            time=e1.time,
        )
        # Recent event causes 'common stats' alert
        action.notify.assert_called_with(alert1)

        cls.assertEqual(
            proc._statsCalculators[0]._timeLastCollectedStats,
            e1.time,
            "Time last collected status must equal latest event",
        )
        cls.assertEqual(1, len(proc._events), "Only one kept within time interval")

        # Too recent to trigger an alert
        proc.consume(e2)
        cls.assertEqual(2, len(proc._events))
        action.notify.assert_called_once()

        # Also too recent
        proc.consume(e3)
        cls.assertEqual(
            3, len(proc._events), "Expecting exactly this many log events collected"
        )
        action.notify.assert_called_once()

        # New interval crossed
        proc.consume(e4)
        cls.assertEqual(4, len(proc._events))

        alert2 = Event(
            priority=Event.Priority.MEDIUM,
            message="Most common section: "
            + f"{e4.section} (4 requests)"
            + ", source: "
            + f"{e4.source} (3 requests)",
            time=e4.time,
        )
        # Expected new frequency event to be generated
        # Expected to only count new events since last generated, no overlapping points
        action.notify.assert_called_with(alert2)

        # Within new interval, shouldn't trigger another event
        proc.consume(e5)

        cls.assertEqual(
            3, len(proc._events), "Expecting exactly this many log events collected"
        )

        cls.assertEqual(
            2, action.notify.call_count, "No more events should be generated"
        )

        # New interval, should have just one event
        e6.section = "/geocities"
        e6.source = "8.8.8.8"
        proc.consume(e6)

        cls.assertEqual(
            1, len(proc._events), "Expecting exactly this many log events collected"
        )

        alert3 = Event(
            priority=Event.Priority.MEDIUM,
            message="Most common section: "
            + f"{e6.section} (1 requests)"
            + ", source: "
            + f"{e6.source} (1 requests)",
            time=e6.time,
        )
        # Expected new frequency event to be generated
        action.notify.assert_called_with(alert3)

    def testHighTrafficWithMostCommonCalculators(cls):
        """Ensure no unenxpected interference when running both,
        and with different interval windows.
        """

        action = MagicMock()
        proc = StatsProcessor(
            action,
            mostCommonStatsInterval=120,
            highTrafficInterval=60,
            highTrafficAvgThreshold=1,
        )

        # Consume a bunch of web events
        now = datetime.strptime("2020-01-01 00:00:00.000000", "%Y-%m-%d %H:%M:%S.%f")

        proc.consume(cls._makeEvent(now + timedelta(minutes=0)))
        proc.consume(cls._makeEvent(now + timedelta(minutes=1)))
        proc.consume(cls._makeEvent(now + timedelta(minutes=2)))
        proc.consume(cls._makeEvent(now + timedelta(minutes=3)))
        proc.consume(cls._makeEvent(now + timedelta(minutes=3)))
        proc.consume(cls._makeEvent(now + timedelta(minutes=4)))
        eventFinal = cls._makeEvent(now + timedelta(minutes=7))
        proc.consume(eventFinal)

        cls.assertEqual(
            5,
            action.notify.call_count,
            "Expected this many stats and high traffic alerts",
        )

        alert = Event(
            priority=Event.Priority.HIGH,
            time=eventFinal.time,
            message=f"Traffic is now back to normal as of {eventFinal.time}",
        )
        action.notify.assert_called_with(alert)

    def testNotImplemented(cls):
        "For better code coverage "

        with cls.assertRaises(NotImplementedError):
            e = cls._makeEvent("2021-03-05")
            Processor(Action()).consume(e)

        with cls.assertRaises(NotImplementedError):
            WindowedCalculator(Action()).count(cls._makeEvent("2021-03-05"))

        with cls.assertRaises(NotImplementedError):
            WindowedCalculator(Action())._removeFromCalculation(
                cls._makeEvent("2021-03-05")
            )

        with cls.assertRaises(NotImplementedError):
            WindowedCalculator(Action())._triggerAlert(cls._makeEvent("2021-03-05"))

        with cls.assertRaises(ValueError):
            MostCommonCalculator(Action()).count(123)

        with cls.assertRaises(ValueError):
            MostCommonCalculator(Action())._removeFromCalculation(123)
