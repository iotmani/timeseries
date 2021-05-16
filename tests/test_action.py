from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from LogsMonitor2000.event import Event
from LogsMonitor2000.action import TerminalNotifier, Action


class TestActionTerminalNotifier(TestCase):
    """ Patch print() to test what it was called with """

    @patch("builtins.print")
    def testNotify(self, mockPrint):
        n = TerminalNotifier()
        event = Event(
            priority=Event.Priority.MEDIUM,
            message="Content",
            time=1620796046,
        )
        n.notify(event)
        self.assertEqual(mockPrint.call_count, 4, "Three for header and one for event")

        # Medium priority is printed with a bold timestamp
        mockPrint.assert_called_with(
            f"\x1b[1m{datetime.fromtimestamp(event.time)}\x1b[0m - {event.message}"
        )

        # High priority is printed with a red timestamp
        event.priority = Event.Priority.HIGH
        n.notify(event)
        mockPrint.assert_called_with(
            f"\x1b[91m{datetime.fromtimestamp(event.time)}\x1b[0m - {event.message}"
        )

        # Just for slightly better code coverage
        with self.assertRaises(NotImplementedError):
            Action().notify(event)
