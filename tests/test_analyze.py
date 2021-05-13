import unittest
from collections import deque
from unittest.mock import MagicMock
from LogsMonitor2000.event import WebLogEvent, Event
from LogsMonitor2000.action import Action
from LogsMonitor2000.analyze import Processor, AnalyticsProcessor
from LogsMonitor2000.analyze.calculator import StreamCalculator
from LogsMonitor2000.analyze.mostCommonCalculator import MostCommonCalculator


class TestAnalyzeAlgorithms(unittest.TestCase):
    "Test analyze module functions"

    def _makeEvent(self, time: int) -> WebLogEvent:
        """ Construct commonly required Event content where only time matters """
        return WebLogEvent(
            time=time,
            priority=WebLogEvent.Priority.MEDIUM,
            message="Some log",
            rfc931=None,
            authuser=None,
            status=None,
            size=None,
            section="/api",
            source="GCHQ",
            request=None,
        )

    def testBufferFullFlush(self):
        """Test bufferred out-of-order events t0 t1 t2 should be all processed once t5 comes in"""

        action = MagicMock()
        # Pick any calculator, we only care check the buffer content and events window
        # Deactivate high traffic calculation
        proc = AnalyticsProcessor(
            action, mostCommonStatsInterval=10, highTrafficInterval=-1
        )

        e0 = self._makeEvent(time=1)
        e1 = self._makeEvent(time=0)
        e2 = self._makeEvent(time=1)
        e3 = self._makeEvent(time=0)
        e4 = self._makeEvent(time=2)
        e5 = self._makeEvent(time=5)

        proc.consume(e0)
        proc.consume(e1)
        proc.consume(e2)
        proc.consume(e3)
        proc.consume(e4)
        proc.consume(e5)

        self.assertEqual(3, len(proc._events), "# of event groups by time in window")
        self.assertEqual(deque([[e1, e3], [e0, e2], [e4]]), proc._events)
        self.assertEqual([e5], proc._buffer, "Buffer must only contains this one event")

    def testBufferFlushOnlyRelevant(self):
        """
        Test buffer flushing of only the events beyond the time
        t1 t0 t2 t3, flushes only t0 and leaves t1 t2 t3
        """

        action = MagicMock()
        # Pick any calculator, we only care about the buffer content
        # Deactivate high traffic calculation
        proc = AnalyticsProcessor(
            action, mostCommonStatsInterval=10, highTrafficInterval=-1
        )

        e0 = self._makeEvent(time=1)
        e1 = self._makeEvent(time=0)
        e2 = self._makeEvent(time=1)
        e3 = self._makeEvent(time=0)
        e4 = self._makeEvent(time=2)
        e5 = self._makeEvent(time=3)

        proc.consume(e0)
        proc.consume(e1)
        proc.consume(e2)
        proc.consume(e3)
        proc.consume(e4)
        proc.consume(e5)

        self.assertEqual(deque([[e1, e3]]), proc._events)
        self.assertEqual(4, len(proc._buffer))

    def testBufferDropTooOld(self):
        """ When t2 processed, and t4 t5 t6 in buffer, drop t1 as too late """

        action = MagicMock()
        # Pick any calculator, we only care about the buffer content
        # Deactivate high traffic calculation
        proc = AnalyticsProcessor(
            action, mostCommonStatsInterval=10, highTrafficInterval=-1
        )

        e0 = self._makeEvent(time=2)
        e1 = self._makeEvent(time=4)
        e2 = self._makeEvent(time=5)
        e3 = self._makeEvent(time=6)
        e4 = self._makeEvent(time=1)

        proc.consume(e0)
        proc.consume(e1)
        proc.consume(e2)
        proc.consume(e3)
        proc.consume(e4)

        self.assertEqual(1, len(proc._events))
        self.assertEqual(3, len(proc._buffer))

    @unittest.skip("Doesnt yet support buffer")
    def testHighTrafficAlerts(self):
        """ Test high traffic and back to normal alerting """

        action = MagicMock()
        # Deactivate other stats calculation to only focus on High Traffic
        # And calculate average over past 2 mins
        # Set High Traffic threshold to x messages during the interval
        proc = AnalyticsProcessor(
            action,
            mostCommonStatsInterval=-1,
            highTrafficInterval=120,
            highTrafficThreshold=3,
        )

        # From normal to High traffic
        e0 = self._makeEvent(time=60 * 0)
        e1 = self._makeEvent(time=60 * 1)
        e2 = self._makeEvent(time=60 * 2)
        e3 = self._makeEvent(time=60 * 3)
        e4 = self._makeEvent(time=60 * 3)
        e5 = self._makeEvent(time=60 * 4)
        proc.consume(e0)
        proc.consume(e1)
        proc.consume(e2)
        self.assertEqual(3, len(proc._events), "All events collected")
        proc.consume(e3)
        self.assertEqual(3, len(proc._events), "First event is outside window")
        # Ensure no high traffic alerts were fired
        self.assertEqual(0, action.notify.call_count, "Did not reach threshold")

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
        self.assertEqual(
            4, len(proc._events), "First two events are now outside window"
        )

        # Back to normal also generates alert
        e6 = self._makeEvent(time=60 * 6)
        proc.consume(e6)
        alertBackToNormal = Event(
            time=e6.time,
            priority=Event.Priority.HIGH,
            message=f"Traffic is now back to normal as of {e6.time}",
        )
        action.notify.assert_called_with(alertBackToNormal)

        e7 = self._makeEvent(time=60 * 9)
        proc.consume(e7)
        self.assertEqual(
            2, action.notify.call_count, "No more alerts as traffic stays low"
        )
        self.assertEqual(1, len(proc._events), "Only one event collected")

        # Traffic up, alert High again
        e8 = self._makeEvent(time=60 * 9)
        e9 = self._makeEvent(time=60 * 9)
        e10 = self._makeEvent(time=60 * 9)
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

    @unittest.skip("Doesnt yet support buffer")
    def testMostCommonStats(self):
        """Test that we generate stats only when expected,
        and with only the relevant events"""

        action = MagicMock()
        # Deactivate high traffic calculation
        proc = AnalyticsProcessor(
            action, mostCommonStatsInterval=10, highTrafficInterval=-1
        )

        e0 = self._makeEvent(time=60 * 0)
        e1 = self._makeEvent(time=60 * 30 + 0)
        e2 = self._makeEvent(time=60 * 30 + 5)
        e3 = self._makeEvent(time=60 * 30 + 9)
        e4 = self._makeEvent(time=60 * 30 + 10)
        e5 = self._makeEvent(time=60 * 30 + 14)
        e6 = self._makeEvent(time=60 * 30 + 58)

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

        e0 = self._makeEvent(time=0)
        e1 = self._makeEvent(time=10)  # Event
        e2 = self._makeEvent(time=11)
        e3 = self._makeEvent(time=12)
        e4 = self._makeEvent(time=20)  # Event
        e5 = self._makeEvent(time=23)  # Buffer flush

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

        proc.consume(self._makeEvent(time=60 * 0))
        proc.consume(self._makeEvent(time=60 * 1))
        proc.consume(self._makeEvent(time=60 * 2))
        proc.consume(self._makeEvent(time=60 * 3))
        proc.consume(self._makeEvent(time=60 * 3))
        proc.consume(self._makeEvent(time=60 * 4))
        eventFinal = self._makeEvent(time=60 * 7)
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

        e0 = self._makeEvent(time=60 * 0)
        e1 = self._makeEvent(time=60 * 1)  # Event, buffer flush
        e2 = self._makeEvent(time=60 * 2)  # Event, buffer flush
        e3 = self._makeEvent(time=60 * 3)  # Event, buffer flush
        e4 = self._makeEvent(time=60 * 4)  # Event, buffer flush
        e5 = self._makeEvent(time=60 * 5)  # Event, buffer flush

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
            e = self._makeEvent(time=1620796046)
            Processor(Action()).consume(e)

        with self.assertRaises(NotImplementedError):
            StreamCalculator(Action()).count([self._makeEvent(time=1620796046)])

        with self.assertRaises(NotImplementedError):
            StreamCalculator(Action()).discount([self._makeEvent(time=1620796046)])

        with self.assertRaises(NotImplementedError):
            StreamCalculator(Action())._triggerAlert(1620796046)

        with self.assertRaises(ValueError):
            MostCommonCalculator(Action()).count([123])

        with self.assertRaises(ValueError):
            MostCommonCalculator(Action()).discount([123])
