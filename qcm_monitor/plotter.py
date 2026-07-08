from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


class Plotter:
    """Manage the frequency and slope plots."""

    def __init__(
        self,
        short_diff_window_points: int = 5,
        average_diff_window_points: int = 20,
        long_diff_window_points: int = 50,
        gate_time_seconds: int = 5,
    ) -> None:
        self.short_diff_window_points = short_diff_window_points
        self.average_diff_window_points = average_diff_window_points
        self.long_diff_window_points = long_diff_window_points
        self.gate_time_seconds = gate_time_seconds

        self.fig = plt.Figure(figsize=(7, 7), dpi=100)
        self.axs = self.fig.subplots(2, 1, sharex=True)
        self.fig.subplots_adjust(wspace=0.0)

        self.finish_freq = 0.0
        self.start_freq = 0.0
        self.slope = 0.0
        self.max_samples = max(2, int(60 * 60 / max(1, self.gate_time_seconds)))

        self.time: list[float] = []
        self.freq_data: list[float] = []
        self.short_diff_data: list[float] = []
        self.long_diff_data: list[float] = []
        self.average_diff_data: list[float] = []

        ax = self.axs[1]
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Slope [Hz/min]")
        ax = self.axs[0]
        ax.set_ylabel("Freq [Hz]")

    def _trim_history(self) -> None:
        if len(self.time) <= self.max_samples:
            return

        excess = len(self.time) - self.max_samples
        del self.time[:excess]
        del self.freq_data[:excess]
        del self.short_diff_data[:excess]
        del self.long_diff_data[:excess]
        del self.average_diff_data[:excess]
        self.time = [index * self.gate_time_seconds for index in range(len(self.freq_data))]

    def _compute_diff_series(self, window_points: int) -> list[float]:
        values: list[float] = []
        for index in range(len(self.freq_data)):
            if index < window_points:
                values.append(float("nan"))
                continue

            x_last = self.time[index - window_points + 1:index + 1]
            y_last = self.freq_data[index - window_points + 1:index + 1]
            slope, _ = np.polyfit(x_last, y_last, 1)
            values.append(slope * 60)
        return values

    def update_plot(self, freq: float) -> None:
        if self.time:
            self.time.append(self.time[-1] + self.gate_time_seconds)
        else:
            self.time.append(0.0)
        self.freq_data.append(freq)

        self.short_diff_data = self._compute_diff_series(self.short_diff_window_points)
        self.average_diff_data = self._compute_diff_series(self.average_diff_window_points)
        self.long_diff_data = self._compute_diff_series(self.long_diff_window_points)
        self._trim_history()
        self.slope = self.average_diff_data[-1] if self.average_diff_data else float("nan")

        ax = self.axs[0]
        ax.clear()
        ax.set_ylabel("Freq [Hz]")
        ax.plot(self.time, self.freq_data, ".b")
        if self.start_freq != 0.0 or self.finish_freq != 0.0:
            ax.axhline(y=self.start_freq, color="gray", linestyle="--", linewidth=1)
            ax.axhline(y=self.finish_freq, color="gray", linestyle="--", linewidth=1)

        ax = self.axs[1]
        ax.clear()
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Slope [Hz/min]")
        ax.plot(self.time, self.short_diff_data, marker="+", linestyle="None", color="red")
        ax.plot(self.time, self.long_diff_data, marker="o", linestyle="None", color="green")
        ax.plot(self.time, self.average_diff_data, marker=".", linestyle="None", color="blue")
        self.fig.canvas.draw_idle()

    def clear_plot(self) -> None:
        self.time = []
        self.freq_data = []
        self.short_diff_data = []
        self.long_diff_data = []
        self.average_diff_data = []
        self.finish_freq = 0.0
        self.start_freq = 0.0
        self.slope = 0.0
        ax = self.axs[1]
        ax.clear()
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Slope [Hz/min]")
        ax = self.axs[0]
        ax.clear()
        ax.set_ylabel("Freq [Hz]")

    def finish_line_plot(self, delta_freq: float) -> None:
        start_freq = self.freq_data[-1] if self.freq_data else 0.0
        self.finish_freq = start_freq - delta_freq
        self.start_freq = start_freq
        self._draw_target_lines()

    def _draw_target_lines(self) -> None:
        ax = self.axs[0]
        ax.axhline(y=self.start_freq, color="gray", linestyle="--", linewidth=1)
        ax.axhline(y=self.finish_freq, color="gray", linestyle="--", linewidth=1)
        self.fig.canvas.draw_idle()
