from unittest import TestCase
from unittest.mock import MagicMock, patch
from LogsMonitor2000.parse import HTTPLogParser, Parser


class TestHTTPLogParser(TestCase):
    """ Simplest test case """

    def testParse(self):
        processor = MagicMock()
        p = HTTPLogParser(processor, "tests/small_sample_csv.txt")
        p.parse()
        # 6 Events plus one call for buffer flush
        self.assertEqual(6, processor.consume.call_count, "Unexpected events number")

    @patch("logging.error")
    def testCsvFileNotFound(self, mockLogging):
        HTTPLogParser(MagicMock(), "tests/non_existent.txt").parse()
        self.assertEqual(mockLogging.call_count, 1)
        mockLogging.assert_called_with(
            "HTTP log file doesn't exist: tests/non_existent.txt"
        )

    @patch("logging.warning")
    def testInvalidCSV(self, mockWarning):
        HTTPLogParser(MagicMock(), "tests/malformed.csv").parse()

        # malformed section
        self.assertEqual(
            mockWarning.mock_calls[0].args[0],
            "Malformed 'section' part of row: ['10.0.0.2', '-', 'apache', '1549573860', 'GET malformed-section HTTP/1.0', '200', '1234']",
        )

        # malformed date
        self.assertEqual(
            mockWarning.mock_calls[1].args[0],
            "Malformed 'date' part of row: ['10.0.0.2', '-', 'apache', 'malformed-date', 'GET /api/user HTTP/1.0', '200', '1234']",
        )

        # missing column
        self.assertEqual(
            mockWarning.mock_calls[2].args[0],
            "Malformed CSV row: ['-', 'missing-column', '1549573860', 'GET /api/user HTTP/1.0', '200', '1234']",
        )

    def testInvalidParser(self):
        "Invalid object instantiation throws errors"
        with self.assertRaises(NotImplementedError):
            Parser(MagicMock()).parse()
