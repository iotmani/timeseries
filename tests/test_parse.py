from event import Event
from parse import HTTPLogParser
from unittest import TestCase
from unittest.mock import MagicMock


class TestHTTPLogParser(TestCase):
    """ Simplest test case """

    def testParse(cls):
        processor = MagicMock()
        p = HTTPLogParser(processor, "tests/small_sample_csv.txt")
        p.parse()
        cls.assertEqual(5, processor.consume.call_count, "Unexpected events number")
