import unittest

from qcm_monitor.app import QCMApp


class InputParsingTests(unittest.TestCase):
    def test_decimal_input_accepts_comma_and_dot(self) -> None:
        app = QCMApp.__new__(QCMApp)

        self.assertEqual(app._parse_decimal("12.5"), 12.5)
        self.assertEqual(app._parse_decimal("12,5"), 12.5)
