import unittest
from .utils import buildEvent
from collections import deque
from unittest.mock import MagicMock
from LogsMonitor2000.analyze import AnalyticsProcessor


class TestBuffering(unittest.TestCase):
    "Test the buffering and buffer flushing parts"

    def testBufferFullFlush(self):
        """Test bufferred out-of-order events t0 t1 t2 should be all processed once t5 comes in"""

        action = MagicMock()
        # Pick any calculator, we only care check the buffer content and events window
        # Deactivate high traffic calculation
        proc = AnalyticsProcessor(
            action, mostCommonStatsInterval=10, highTrafficInterval=-1
        )

        e0 = buildEvent(time=1)
        e1 = buildEvent(time=0)
        e2 = buildEvent(time=1)
        e3 = buildEvent(time=0)
        e4 = buildEvent(time=2)
        e5 = buildEvent(time=5)

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

        e0 = buildEvent(time=1)
        e1 = buildEvent(time=0)
        e2 = buildEvent(time=1)
        e3 = buildEvent(time=0)
        e4 = buildEvent(time=2)
        e5 = buildEvent(time=3)

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

        e0 = buildEvent(time=2)
        e1 = buildEvent(time=4)
        e2 = buildEvent(time=5)
        e3 = buildEvent(time=6)
        e4 = buildEvent(time=1)

        proc.consume(e0)
        proc.consume(e1)
        proc.consume(e2)
        proc.consume(e3)
        proc.consume(e4)

        self.assertEqual(1, len(proc._events))
        self.assertEqual(3, len(proc._buffer))
