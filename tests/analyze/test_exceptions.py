import unittest
from .utils import buildEvent
from unittest.mock import MagicMock
from LogsMonitor2000.analyze import Processor
from LogsMonitor2000.analyze.calculator import StreamCalculator
from LogsMonitor2000.analyze.mostCommonCalculator import MostCommonCalculator


class TestExceptions(unittest.TestCase):
    "Test exceptions are thrown as expected"

    def testExpectionsThrown(self):
        "Invalid object instantiations throw errors"
        action = MagicMock()

        with self.assertRaises(ValueError):
            MostCommonCalculator(action, []).count([123])

        with self.assertRaises(ValueError):
            MostCommonCalculator(action, []).discount([123])

        e = buildEvent(time=1620796046)
        with self.assertRaises(NotImplementedError):
            StreamCalculator(action, []).count([e])

        with self.assertRaises(NotImplementedError):
            StreamCalculator(action, []).discount([e])

        with self.assertRaises(NotImplementedError):
            StreamCalculator(action, []).triggerAlert(e.time)

        with self.assertRaises(NotImplementedError):
            Processor(action).consume(e)
