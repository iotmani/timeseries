from event import Event
from action import TerminalNotifier, Action
from unittest import TestCase
from unittest.mock import patch


class TestActionTerminalNotifier(TestCase):
    """ Patch print() to test what it was called with """

    @patch("builtins.print")
    def testNotify(cls, mock_print):
        n = TerminalNotifier()
        event = Event(
            priority=Event.Priority.MEDIUM,
            message="Content",
            time="2021-03-05",
        )
        n.notify(event)
        cls.assertEqual(mock_print.call_count, 4)
        mock_print.assert_called_with(event)

        event.priority = Event.Priority.HIGH
        n.notify(event)
        mock_print.assert_called_with(event)

        # Just for better code coverage
        with cls.assertRaises(NotImplementedError):
            Action().notify(event)
