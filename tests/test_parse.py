from unittest import TestCase
from unittest.mock import MagicMock
from LogsMonitor2000.event import Event
from LogsMonitor2000.parse import HTTPLogParser


class TestHTTPLogParser(TestCase):
    """ Simplest test case """

    def testParse(self):
        processor = MagicMock()
        p = HTTPLogParser(processor, "tests/small_sample_csv.txt")
        p.parse()
        self.assertEqual(5, processor.consume.call_count, "Unexpected events number")
