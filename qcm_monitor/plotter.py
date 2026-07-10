from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt


class Plotter:
    """Manage the frequency and slope plots with a rolling 1-hour view."""

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

        self.fig = plt.Figure(figsize=(6, 7), dpi=100)
        self.axs = self.fig.subplots(2, 1, sharex=True)
        self.fig.subplots_adjust(
            left=0.15,    # 15% padding on the left for Y-axis labels (e.g., "Freq [Hz]")
            right=0.95,   # 5% padding on the right side
            top=0.95,     # Leaves space at the very top of the figure
            bottom=0.1,  # 10% padding at the bottom of the lower plot for X-axis labels
            wspace=0.0,   # No horizontal space between subplots (since they are stacked vertically)
            hspace=0.1   # Slightly tighter vertical gap between the top and bottom plots
        )
        self.finish_freq = 0.0
        self.start_freq = 0.0
        self.slope = 0.0

        self.time: list[float] = []
        self.freq_data: list[float] = []
        self.short_diff_data: list[float] = []
        self.long_diff_data: list[float] = []
        self.average_diff_data: list[float] = []

        ax = self.axs[1]
        ax.set_xlabel("Time [min]")
        ax.set_ylabel("Slope [Hz/min]")
        ax.set_ylim(None, 1.0)
        ax = self.axs[0]
        ax.set_ylabel("Freq [Hz]")

    def _update_axis_limits(self, current_time_min: float) -> None:
        """Let Matplotlib autoscale at the beginning, then slide the window past 60 mins with padding."""
        ax = self.axs[1]  # Bottom axis handles xlim because sharex=True
        
        if current_time_min > 60.0:
            # Use NumPy to round up to the nearest integer
            upper_limit = np.ceil(current_time_min)
            lower_limit = upper_limit - 60.0
            
            ax.set_xlim(lower_limit, upper_limit)
        else:
            # Under 60 minutes, explicitly tell the axis to autoscale natively
            ax.relim()
            ax.autoscale_view(True, True, False)  # Autoscale X and Y

    def _compute_diff_series(self, window_points: int) -> list[float]:
        values: list[float] = []
        for index in range(len(self.freq_data)):
            if index < window_points:
                values.append(float("nan"))
                continue

            x_last = self.time[index - window_points + 1:index + 1]
            y_last = self.freq_data[index - window_points + 1:index + 1]
            slope, _ = np.polyfit(x_last, y_last, 1)
            values.append(slope)
        return values
    
    def update_plot(self, freq: float) -> None:
        if self.time:
            current_time = self.time[-1] + (self.gate_time_seconds / 60.0)
        else:
            current_time = 0.0
            
        self.time.append(current_time)
        self.freq_data.append(freq)

        self.short_diff_data = self._compute_diff_series(self.short_diff_window_points)
        self.average_diff_data = self._compute_diff_series(self.average_diff_window_points)
        self.long_diff_data = self._compute_diff_series(self.long_diff_window_points)
        self.slope = self.average_diff_data[-1] if self.average_diff_data else float("nan")

        # Render Top Plot
        ax = self.axs[0]
        ax.clear()
        ax.set_ylabel("Freq [Hz]")
        # Changed from dark blue to high-visibility cyan (marker '.')
        ax.plot(self.time, self.freq_data, marker=".", linestyle="None", color="#00e5ff")
        
        if self.start_freq != 0.0 or self.finish_freq != 0.0:
            # Changed to a brighter, slightly translucent light gray/white line
            ax.axhline(y=self.start_freq, color="#aaaaaa", linestyle="--", linewidth=1, alpha=0.7)
            ax.axhline(y=self.finish_freq, color="#aaaaaa", linestyle="--", linewidth=1, alpha=0.7)

        # Render Bottom Plot
        ax = self.axs[1]
        ax.clear()
        ax.set_xlabel("Time [min]")
        ax.set_ylabel("Slope [Hz/min]")
        
        # Swapped to bright neon/pastel dark-mode variations
        ax.plot(self.time, self.short_diff_data, marker="+", linestyle="None", color="#ff5252")  # Bright Coral Red
        #ax.plot(self.time, self.long_diff_data, marker="o", linestyle="None", color="#00e676")   # Neon Lime Green
        ax.plot(self.time, self.average_diff_data, marker=".", linestyle="None", color="#00e676") # Bright Cyan
        
        # Apply the adaptive scale rule
        self._update_axis_limits(current_time)
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
        ax.set_xlabel("Time [min]")
        ax.set_ylabel("Slope [Hz/min]")
        ax.set_xlim(0.0, 1.0)  # Reset viewport tight to start
        
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
