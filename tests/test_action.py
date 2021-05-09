from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from LogsMonitor2000.event import Event
from LogsMonitor2000.action import TerminalNotifier, Action


class TestActionTerminalNotifier(TestCase):
    """ Patch print() to test what it was called with """

    @patch("builtins.print")
    def testNotify(cls, mock_print):
        n = TerminalNotifier()
        event = Event(
            priority=Event.Priority.MEDIUM,
            message="Content",
            time=datetime.fromisoformat("2021-03-05"),
        )
        n.notify(event)
        cls.assertEqual(mock_print.call_count, 4)
        mock_print.assert_called_with(f"\x1b[1m{event.time}\x1b[0m - {event.message}")

        event.priority = Event.Priority.HIGH
        n.notify(event)
        mock_print.assert_called_with(f"\x1b[91m{event.time}\x1b[0m - {event.message}")

        # Just for better code coverage
        with cls.assertRaises(NotImplementedError):
            Action().notify(event)
