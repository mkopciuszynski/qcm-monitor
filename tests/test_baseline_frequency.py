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
        app.last_abs_freq = 100.0
        app.reader = type("Reader", (), {"last_successful_frequency": 100.0})()

        self.assertEqual(app._resolve_frequency(0.0), 100.0)
        self.assertEqual(app.last_abs_freq, 100.0)

    def test_decimal_input_accepts_comma_and_dot(self) -> None:
        app = QCMApp.__new__(QCMApp)

        self.assertEqual(app._parse_decimal("12.5"), 12.5)
        self.assertEqual(app._parse_decimal("12,5"), 12.5)

    def test_anomaly_does_not_overwrite_last_good_frequency(self) -> None:
        app = QCMApp.__new__(QCMApp)
        app.last_abs_freq = 100.0

        self.assertEqual(app._resolve_frequency(300.0), 100.0)
        self.assertEqual(app.last_abs_freq, 100.0)

        self.assertEqual(app._resolve_frequency(100.5), 100.5)
        self.assertEqual(app.last_abs_freq, 100.5)

    def test_plotter_average_window_uses_configured_points(self) -> None:
        plotter = Plotter(short_diff_window_points=2, long_diff_window_points=4, average_diff_window_points=3, gate_time_seconds=1)
        for freq in [0.0, 1.0, 2.0, 3.0]:
            plotter.update_plot(freq)

        self.assertFalse(math.isnan(plotter.average_diff_data[-1]))

    def test_app_prunes_history_using_max_history_points(self) -> None:
        app = QCMApp.__new__(QCMApp)
        app.settings = type("Settings", (), {"app": type("AppConfig", (), {"max_history_points": 720})()})()
        app.plotter = Plotter(gate_time_seconds=5, max_history_points=720)
        app.plotter.time = list(range(800))
        app.plotter.freq_data = [float(v) for v in range(800)]
        app.plotter.short_diff_data = [float(v) for v in range(800)]
        app.plotter.average_diff_data = [float(v) for v in range(800)]
        app.plotter.long_diff_data = [float(v) for v in range(800)]

        max_history_points = getattr(app.settings.app, "max_history_points", 3600)
        for attr_name in [
            "time",
            "freq_data",
            "short_diff_data",
            "average_diff_data",
            "long_diff_data",
        ]:
            attr_list = getattr(app.plotter, attr_name, None)
            if isinstance(attr_list, list) and len(attr_list) > max_history_points:
                setattr(app.plotter, attr_name, attr_list[-max_history_points:])

        self.assertEqual(len(app.plotter.time), 720)
        self.assertEqual(len(app.plotter.freq_data), 720)
        self.assertEqual(len(app.plotter.short_diff_data), 720)
        self.assertEqual(len(app.plotter.average_diff_data), 720)
        self.assertEqual(len(app.plotter.long_diff_data), 720)


if __name__ == "__main__":
    unittest.main()
