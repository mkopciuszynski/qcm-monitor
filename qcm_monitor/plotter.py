from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


class Plotter:
    """Manage the frequency and slope plots."""

    def __init__(self, diff_window_points: int = 5, slope_window_points: int = 50) -> None:
        self.diff_window_points = diff_window_points
        self.slope_window_points = slope_window_points

        self.fig = plt.Figure(figsize=(7, 8), dpi=100)
        self.axs = self.fig.subplots(2, 1, sharex=True)
        self.fig.subplots_adjust(wspace=0.0)

        self.finish_freq = 0.0
        self.start_freq = 0.0
        self.slope = 0.0

        self.time: list[float] = []
        self.freq_data: list[float] = []
        self.diff_data: list[float] = []

        ax = self.axs[1]
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Diff [Hz/min]")
        ax = self.axs[0]
        ax.set_ylabel("Freq [Hz]")

    def update_plot(self, freq: float) -> None:
        self.time.append(len(self.time) * 5)
        self.freq_data.append(freq)
        if len(self.time) > self.diff_window_points:
            x_last = self.time[-self.diff_window_points:]
            y_last = self.freq_data[-self.diff_window_points:]
            slope, _ = np.polyfit(x_last, y_last, 1)
            self.diff_data.append(slope * 60)
        else:
            self.diff_data.append(-0.0001)

        if len(self.time) > self.slope_window_points:
            x_last = self.time[-self.slope_window_points:]
            y_last = self.freq_data[-self.slope_window_points:]
            slope, _ = np.polyfit(x_last, y_last, 1)
            self.slope = slope * 60

        ax = self.axs[0]
        ax.relim()
        ax.autoscale_view()
        ax.plot(self.time[-1], self.freq_data[-1], ".b")

        ax = self.axs[1]
        ax.relim()
        ax.autoscale_view()
        ax.plot(self.time[-1], self.diff_data[-1], ".r")
        self.fig.canvas.draw_idle()

    def clear_plot(self) -> None:
        self.time = []
        self.freq_data = []
        self.diff_data = []
        self.finish_freq = 0.0
        self.start_freq = 0.0
        self.slope = 0.0
        ax = self.axs[1]
        ax.clear()
        ax.set_xlabel("Time [s]")
        ax.set_ylabel("Diff [Hz/min]")
        ax = self.axs[0]
        ax.clear()
        ax.set_ylabel("Freq [Hz]")

    def finish_line_plot(self, delta_freq: float) -> None:
        if not self.freq_data:
            return
        start_freq = self.freq_data[-1]
        self.finish_freq = start_freq - delta_freq
        self.start_freq = start_freq
        ax = self.axs[0]
        ax.axhline(y=self.finish_freq)
        ax.axhline(y=self.start_freq)
