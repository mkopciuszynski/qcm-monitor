import unittest

from qcm_monitor.app import QCMApp


class FrequencyFilterTests(unittest.TestCase):
    def test_relative_frequency_uses_first_successful_reading(self) -> None:
        app = QCMApp.__new__(QCMApp)
        app.reference_freq = None

        self.assertEqual(app._relative_frequency(100.0), 0.0)
        self.assertEqual(app.reference_freq, 100.0)
        self.assertEqual(app._relative_frequency(112.5), 12.5)

    def test_parse_failure_uses_last_successful_reading(self) -> None:
        app = QCMApp.__new__(QCMApp)
        app.reference_freq = None
        app.last_abs_freq = 100.0
        app.reader = type("Reader", (), {"last_successful_frequency": 100.0})()

        self.assertEqual(app._resolve_frequency(0.0), 100.0)
        self.assertEqual(app.last_abs_freq, 100.0)

    def test_anomaly_does_not_overwrite_last_good_frequency(self) -> None:
        app = QCMApp.__new__(QCMApp)
        app.last_abs_freq = 100.0

        self.assertEqual(app._resolve_frequency(300.0), 100.0)
        self.assertEqual(app.last_abs_freq, 100.0)

        self.assertEqual(app._resolve_frequency(100.5), 100.5)
        self.assertEqual(app.last_abs_freq, 100.5)
