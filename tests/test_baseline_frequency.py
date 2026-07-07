import math
import unittest

from qcm_monitor.app import QCMApp
from qcm_monitor.plotter import Plotter


class BaselineFrequencyTests(unittest.TestCase):
    def test_relative_frequency_uses_first_successful_reading(self) -> None:
        app = QCMApp.__new__(QCMApp)
        app.reference_freq = None

        self.assertEqual(app._relative_frequency(100.0), 0.0)
        self.assertEqual(app.reference_freq, 100.0)
        self.assertEqual(app._relative_frequency(112.5), 12.5)

    def test_parse_failure_uses_last_successful_reading(self) -> None:
        app = QCMApp.__new__(QCMApp)
        app.reference_freq = None
        app.reader = type("Reader", (), {"last_successful_frequency": 100.0})()

        raw_freq, display_freq = app._resolve_frequency(0.0)

        self.assertEqual(raw_freq, 100.0)
        self.assertEqual(display_freq, 0.0)

    def test_decimal_input_accepts_comma_and_dot(self) -> None:
        app = QCMApp.__new__(QCMApp)

        self.assertEqual(app._parse_decimal("12.5"), 12.5)
        self.assertEqual(app._parse_decimal("12,5"), 12.5)

    def test_plotter_average_window_uses_configured_points(self) -> None:
        plotter = Plotter(short_diff_window_points=2, long_diff_window_points=4, average_diff_window_points=3, gate_time_seconds=1)
        for freq in [0.0, 1.0, 2.0, 3.0]:
            plotter.update_plot(freq)

        self.assertFalse(math.isnan(plotter.average_diff_data[-1]))


if __name__ == "__main__":
    unittest.main()
