from __future__ import annotations

import tkinter as tk
import winsound
from datetime import datetime
from pathlib import Path
from typing import Optional

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .config import Settings, load_settings, save_settings
from .plotter import Plotter
from .serial_reader import SerialFrequencyReader


class QCMApp:
    """Main application window for QCM monitoring."""

    def __init__(self, settings_path: Optional[Path] = None) -> None:
        self.settings = load_settings(settings_path)
        self.reader = SerialFrequencyReader(self.settings.serial)
        self.plotter = Plotter(
            diff_window_points=self.settings.plot.diff_window_points,
            slope_window_points=self.settings.plot.slope_window_points,
        )
        self.delta_freq: Optional[float] = None
        self.time_left: Optional[float] = None
        self.freq_left: Optional[float] = None

        self.root = tk.Tk()
        self.root.title(self.settings.app.window_title)
        self.root.geometry(f"{self.settings.app.window_width}x{self.settings.app.window_height}+0+0")
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        self.canvas = FigureCanvasTkAgg(self.plotter.fig, master=self.root)
        self.canvas.get_tk_widget().pack()

        self.message_text = tk.Text(self.root, height=25, width=60)
        self.message_text.pack(side=tk.LEFT)

        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(side=tk.LEFT, padx=20, fill="x")

        self.reset_button = tk.Button(self.button_frame, text="Clear", width=10, command=self.button_reset)
        self.input_entry = tk.Entry(self.button_frame, width=10)
        self.start_button = tk.Button(self.button_frame, text="Start", width=10, command=self.button_start)
        self.exit_button = tk.Button(self.button_frame, text="Exit", width=10, command=self.exit_app)

        self.input_entry.grid(row=1, column=1, padx=2, pady=20)
        self.start_button.grid(row=1, column=2, padx=2, pady=20)
        self.reset_button.grid(row=2, column=1, padx=2, pady=20)
        self.exit_button.grid(row=2, column=2, padx=2, pady=20)

        self.update_loop()

    def run(self) -> None:
        self.root.mainloop()

    def exit_app(self) -> None:
        self.reader.close()
        self.root.destroy()

    def update_loop(self) -> None:
        current_time = datetime.now()
        self.message_text.delete(1.0, tk.END)
        self.message_text.insert(tk.END, current_time.strftime("%H:%M:%S%z"))
        self.message_text.insert(tk.END, ": ")

        last_freq = self.reader.read_frequency()
        last_freq -= self.settings.serial.zero_frequency
        self.plotter.update_plot(last_freq)

        self.message_text.insert(tk.END, "\nLast freq Hz: ")
        self.message_text.insert(tk.END, f"{last_freq:.4f}")
        self.message_text.insert(tk.END, "\nDiff Hz/min: ")
        self.message_text.insert(tk.END, f"{self.plotter.diff_data[-1]:.4f}")
        self.message_text.insert(tk.END, "\nSlope (last 50 points) Hz/min: ")
        self.message_text.insert(tk.END, f"{self.plotter.slope:.4f}")
        self.message_text.insert(tk.END, "\n")

        if self.plotter.finish_freq > 0 and self.plotter.diff_data:
            self.freq_left = self.plotter.freq_data[-1] - self.plotter.finish_freq
            self.time_left = -(self.plotter.freq_data[-1] - self.plotter.finish_freq) / self.plotter.diff_data[-1]
            self.message_text.insert(tk.END, "\nFreq left [Hz]: ")
            self.message_text.insert(tk.END, f"{self.freq_left:.2f}")
            self.message_text.insert(tk.END, "\nTime left [min]: ")
            self.message_text.insert(tk.END, f"{self.time_left:.2f}")
            if self.time_left < self.settings.app.beep_threshold_minutes:
                winsound.Beep(2500, self.settings.app.beep_duration_ms)
            if self.time_left < 0:
                winsound.Beep(2500, self.settings.app.beep_warning_ms)

        time_difference = datetime.now() - current_time
        new_time = int(time_difference.total_seconds() * 1000)
        delay_ms = self.settings.app.gate_time_seconds * 1000 - new_time
        self.root.after(max(100, delay_ms), self.update_loop)

    def button_reset(self) -> None:
        self.plotter.clear_plot()
        self.message_text.insert(tk.END, "\n======Clear======\n")

    def button_start(self) -> None:
        self.message_text.insert(tk.END, "\n======Start======\n")
        try:
            self.delta_freq = float(self.input_entry.get())
        except ValueError:
            self.delta_freq = 0.0
        if self.delta_freq is not None:
            self.plotter.finish_line_plot(self.delta_freq)


def create_app(settings_path: Optional[Path] = None) -> QCMApp:
    return QCMApp(settings_path=settings_path)
