import unittest
from .utils import buildEvent
from datetime import datetime
from collections import deque
from unittest.mock import MagicMock
from LogsMonitor2000.event import Event
from LogsMonitor2000.action import Action
from LogsMonitor2000.analyze import Processor, AnalyticsProcessor
from LogsMonitor2000.analyze.calculator import StreamCalculator
from LogsMonitor2000.analyze.mostCommonCalculator import MostCommonCalculator


class TestCalculatorsInterval(unittest.TestCase):
    """
    Ensure events are collected, ordered correctly and removed when they
    fall outside the sliding window time interval.
    """

    def testInterval(self):
        action = MagicMock()
        # Set an interval for any calculator, events are collected for the largest window
        proc = AnalyticsProcessor(
            action,
            mostCommonStatsInterval=100,
            highTrafficInterval=120,
        )

        # All within 120s interval
        e0 = buildEvent(time=60 * 2)
        e1 = buildEvent(time=60 * 1)
        e2 = buildEvent(time=60 * 0)
        e3 = buildEvent(time=60 * 1)
        e4 = buildEvent(time=60 * 2)
        # Goes above 120s, kicking out the e2 event at t=0
        e5 = buildEvent(time=60 * 3)

        # Make slightly different to ensure order is correct within grouped events
        e1.message = "bladi"
        e0.message = "blah"
        proc.consume(e0)
        proc.consume(e1)
        proc.consume(e2)
        proc.consume(e3)
        proc.consume(e4)

        proc.consume(None)
        self.assertEqual(3, len(proc._events), "All events so far are within interval")
        self.assertEqual(deque([[e2], [e1, e3], [e0, e4]]), proc._events)
        proc.consume(e5)
        proc.consume(None)
        self.assertEqual(3, len(proc._events), "First event is now outside window")
        self.assertEqual(deque([[e1, e3], [e0, e4], [e5]]), proc._events)

        e6 = buildEvent(60 * 60)
        proc.consume(e6)
        proc.consume(None)
        self.assertEqual(1, len(proc._events), "All but one events remain")
        self.assertEqual(deque([[e6]]), proc._events)


class TestCalculatorsAlerting(unittest.TestCase):
    "Test statistics calculation logic for high traffic alerts and most common stats"

    def testHighTrafficAlerts(self):
        """ Test high traffic and back to normal alerting """

        action = MagicMock()
        # Deactivate other stats calculation to only focus on High Traffic
        # And calculate average over past 2 mins
        # Set High Traffic threshold to x messages during the interval
        proc = AnalyticsProcessor(
            action,
            mostCommonStatsInterval=-1,
            highTrafficInterval=3,
            highTrafficThreshold=2,
        )

        # From normal to High traffic
        proc.consume(buildEvent(time=0))
        proc.consume(buildEvent(time=1))
        proc.consume(buildEvent(time=2))
        proc.consume(buildEvent(time=3))
        proc.consume(buildEvent(time=3))
        proc.consume(buildEvent(time=3))
        proc.consume(None)
        # Ensure no high traffic alerts were fired
        self.assertEqual(0, action.notify.call_count, "Did not reach threshold")

        # Add 3 more to go from 2tps to 2.33tps
        proc.consume(buildEvent(time=3))
        proc.consume(None)
        self.assertEqual(proc._statsCalculators[0]._average, 2.3333333333333335)
        # Traffic increases but must not alert again
        proc.consume(buildEvent(time=3))
        proc.consume(buildEvent(time=3))
        proc.consume(buildEvent(time=3))
        proc.consume(None)
        self.assertEqual(proc._statsCalculators[0]._average, 3.3333333333333335)
        # Check High Traffic alert fired only once
        self.assertEqual(1, action.notify.call_count, "Only alerted once")
        alertHighTraffic = Event(
            time=3,
            priority=Event.Priority.HIGH,
            message="High traffic generated an alert - "
            f"hits 2.33, triggered at {datetime.fromtimestamp(3)}",
        )
        action.notify.assert_called_with(alertHighTraffic)

        # Back to normal also generates alert
        e6 = buildEvent(time=7)
        proc.consume(e6)
        proc.consume(None)
        self.assertEqual(proc._statsCalculators[0]._average, 1.6666666666666667)
        alertBackToNormal = Event(
            time=e6.time,
            priority=Event.Priority.HIGH,
            message=f"Traffic is now back to normal as of {datetime.fromtimestamp(e6.time)}",
        )
        action.notify.assert_called_with(alertBackToNormal)
        self.assertEqual(2, action.notify.call_count, "High and Back to Normal alerts")

        e7 = buildEvent(time=9)
        proc.consume(e7)
        proc.consume(None)
        self.assertEqual(proc._statsCalculators[0]._average, 2.0)
        self.assertEqual(2, action.notify.call_count, "Traffic stays within threshold")

        # Traffic back up, alert High Traffic again
        e8 = buildEvent(time=9)
        e9 = buildEvent(time=9)
        e10 = buildEvent(time=9)
        proc.consume(e8)
        proc.consume(e9)
        proc.consume(e10)
        proc.consume(None)
        self.assertEqual(proc._statsCalculators[0]._average, 3)
        alertHighTraffic = Event(
            time=e10.time,
            priority=Event.Priority.HIGH,
            message="High traffic generated an alert - "
            f"hits 3.00, triggered at {datetime.fromtimestamp(e10.time)}",
        )
        action.notify.assert_called_with(alertHighTraffic)

    @unittest.skip("Doesnt yet support buffer")
    def testMostCommonStats(self):
        """Test that we generate stats only when expected,
        and with only the relevant events"""

        action = MagicMock()
        # Deactivate high traffic calculation
        proc = AnalyticsProcessor(
            action, mostCommonStatsInterval=10, highTrafficInterval=-1
        )

        e0 = buildEvent(time=60 * 0)
        e1 = buildEvent(time=60 * 30 + 0)
        e2 = buildEvent(time=60 * 30 + 5)
        e3 = buildEvent(time=60 * 30 + 9)
        e4 = buildEvent(time=60 * 30 + 10)
        e5 = buildEvent(time=60 * 30 + 14)
        e6 = buildEvent(time=60 * 30 + 58)

        proc.consume(e0)
        self.assertEqual(
            e0.time,
            proc._statsCalculators[0]._timeLastCollectedStats,
            "Time last collected stats must equal first and only event's time",
        )
        self.assertEqual(
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

        self.assertEqual(
            proc._statsCalculators[0]._timeLastCollectedStats,
            e1.time,
            "Time last collected status must equal latest event",
        )
        self.assertEqual(1, len(proc._events), "Only one kept within time interval")

        # Too recent to trigger an alert
        proc.consume(e2)
        self.assertEqual(2, len(proc._events))
        action.notify.assert_called_once()

        # Also too recent
        proc.consume(e3)
        self.assertEqual(
            3, len(proc._events), "Expecting exactly this many log events collected"
        )
        action.notify.assert_called_once()

        # New interval crossed
        proc.consume(e4)
        self.assertEqual(4, len(proc._events))

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

        self.assertEqual(
            3, len(proc._events), "Expecting exactly this many log events collected"
        )

        self.assertEqual(
            2, action.notify.call_count, "No more events should be generated"
        )

        # New interval, should have just one event
        e6.section = "/geocities"
        e6.source = "8.8.8.8"
        proc.consume(e6)

        self.assertEqual(
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

    def testMostCommonStatsBuffered(self):
        """
        Test that we fire most common stats events only when expected,
        and with only the relevant events.
        """

        action = MagicMock()
        # Deactivate high traffic calculation
        proc = AnalyticsProcessor(
            action, mostCommonStatsInterval=10, highTrafficInterval=-1
        )

        e0 = buildEvent(time=0)
        e1 = buildEvent(time=10)  # Event
        e2 = buildEvent(time=11)
        e3 = buildEvent(time=12)
        e4 = buildEvent(time=20)  # Event
        e5 = buildEvent(time=23)  # Buffer flush

        e1.section = "/ping"
        e1.source = "NSA"
        e2.source = "NSA"
        proc.consume(e0)
        proc.consume(e1)
        proc.consume(e2)
        proc.consume(e3)
        # Only first processed
        self.assertEqual(
            e0.time,
            proc._statsCalculators[0]._timeLastCollectedStats,
            "Time last collected stats must equal first and only event's time",
        )

        self.assertEqual(
            0,
            action.notify.call_count,
            "No notification generated from first ever event",
        )

        proc.consume(e4)
        proc.consume(e5)
        self.assertEqual(
            proc._statsCalculators[0]._timeLastCollectedStats,
            e4.time,
            "Time last collected status must equal latest processed event (excl buffered one)",
        )
        self.assertEqual(
            4,
            len(proc._events),
            "Exactly this many processed and within sliding window",
        )

        # Recent event causes 'common stats' alert
        alert1 = Event(
            priority=Event.Priority.MEDIUM,
            message="Most common section: "
            + f"{e4.section} (3 requests)"
            + ", source: "
            + f"{e4.source} (2 requests)",
            time=e4.time,
        )
        action.notify.assert_called_with(alert1)

    @unittest.skip("Doesnt yet support buffer")
    def testHighTrafficWithMostCommonCalculators(self):
        """Ensure no unenxpected interference when running both,
        and with different interval windows.
        """

        action = MagicMock()
        proc = AnalyticsProcessor(
            action,
            mostCommonStatsInterval=120,
            highTrafficInterval=60,
            highTrafficThreshold=1,
        )

        proc.consume(buildEvent(time=60 * 0))
        proc.consume(buildEvent(time=60 * 1))
        proc.consume(buildEvent(time=60 * 2))
        proc.consume(buildEvent(time=60 * 3))
        proc.consume(buildEvent(time=60 * 3))
        proc.consume(buildEvent(time=60 * 4))
        eventFinal = buildEvent(time=60 * 7)
        proc.consume(eventFinal)

        self.assertEqual(
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

    def testMostCommonStatsSpacedEvents(self):
        """
        Test behavior is correct when there's a large time difference between events
        """

        action = MagicMock()
        # Deactivate high traffic calculation
        proc = AnalyticsProcessor(
            action, mostCommonStatsInterval=10, highTrafficInterval=-1
        )

        e0 = buildEvent(time=60 * 0)
        e1 = buildEvent(time=60 * 1)  # Event, buffer flush
        e2 = buildEvent(time=60 * 2)  # Event, buffer flush
        e3 = buildEvent(time=60 * 3)  # Event, buffer flush
        e4 = buildEvent(time=60 * 4)  # Event, buffer flush
        e5 = buildEvent(time=60 * 5)  # Event, buffer flush

        proc.consume(e0)
        proc.consume(e1)
        proc.consume(e2)
        proc.consume(e3)
        proc.consume(e4)
        proc.consume(e5)
        self.assertEqual(
            e4.time,
            proc._statsCalculators[0]._timeLastCollectedStats,
            "Time last collected status must equal latest processed event (excl buffered one)",
        )

        self.assertEqual(
            4,
            action.notify.call_count,
            "All processed except e5 buffered, all notified up to and excluding e4.",
        )

    def testNotImplemented(self):
        "For better code coverage "

        with self.assertRaises(NotImplementedError):
            e = buildEvent(time=1620796046)
            Processor(Action()).consume(e)

        with self.assertRaises(NotImplementedError):
            StreamCalculator(Action(), []).count([buildEvent(time=1620796046)])

        with self.assertRaises(NotImplementedError):
            StreamCalculator(Action(), []).discount([buildEvent(time=1620796046)])

        with self.assertRaises(NotImplementedError):
            StreamCalculator(Action(), [])._triggerAlert(1620796046)

        with self.assertRaises(ValueError):
            MostCommonCalculator(Action(), []).count([123])

        with self.assertRaises(ValueError):
            MostCommonCalculator(Action(), []).discount([123])
