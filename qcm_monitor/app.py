from __future__ import annotations

import tkinter as tk
import winsound
from datetime import datetime
from pathlib import Path
from typing import Optional

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .config import load_settings
from .plotter import Plotter
from .serial_reader import SerialFrequencyReader


class QCMApp:
    """Main application window for QCM monitoring."""

    def __init__(self, settings_path: Optional[Path] = None) -> None:
        self.settings = load_settings(settings_path)
        self.reader = SerialFrequencyReader(self.settings.serial)
        self.plotter = Plotter(
            short_diff_window_points=self.settings.app.short_velocity_window_points,
            long_diff_window_points=self.settings.app.long_velocity_window_points,
            gate_time_seconds=self.settings.app.gate_time_seconds,
        )
        self.delta_freq: Optional[float] = None
        self.time_left: Optional[float] = None
        self.freq_left: Optional[float] = None
        self.reference_freq: Optional[float] = None

        self.root = tk.Tk()
        self.root.title("QCM Monitor")
        self.root.geometry(f"{self.settings.app.window_width}x{self.settings.app.window_height}+0+0")
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.plot_frame = tk.Frame(self.main_frame)
        self.plot_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = FigureCanvasTkAgg(self.plotter.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.bottom_frame = tk.Frame(self.main_frame)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.message_text = tk.Text(self.bottom_frame, height=18, width=60)
        self.message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.button_frame = tk.Frame(self.bottom_frame)
        self.button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

        self.input_entry = tk.Entry(self.button_frame, width=12)
        self.start_button = tk.Button(self.button_frame, text="Start", width=10, command=self.button_start)
        self.reset_button = tk.Button(self.button_frame, text="Clear", width=10, command=self.button_reset)
        self.exit_button = tk.Button(self.button_frame, text="Exit", width=10, command=self.exit_app)

        self.input_entry.grid(row=0, column=0, padx=2, pady=4)
        self.start_button.grid(row=0, column=1, padx=2, pady=4)
        self.reset_button.grid(row=1, column=0, padx=2, pady=4)
        self.exit_button.grid(row=1, column=1, padx=2, pady=4)

        self.status_label = tk.Label(self.root, text="", anchor=tk.W)
        self.status_label.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.root.after(100, self._refresh_status)

    def run(self) -> None:
        self.root.mainloop()

    def _refresh_status(self) -> None:
        current_time = datetime.now()
        self.message_text.delete(1.0, tk.END)
        self.message_text.insert(tk.END, current_time.strftime("%H:%M:%S%z"))
        self.message_text.insert(tk.END, ": ")

        print(f"[app] refresh cycle at {current_time.strftime('%H:%M:%S')}")
        raw_freq = self.reader.read_frequency()
        plotted_freq, display_freq = self._resolve_frequency(raw_freq)
        self.plotter.update_plot(display_freq)

        self.message_text.insert(tk.END, "\nRaw freq Hz: ")
        self.message_text.insert(tk.END, f"{raw_freq:.4f}")
        self.message_text.insert(tk.END, "\nDisplay freq Hz: ")
        self.message_text.insert(tk.END, f"{display_freq:.4f}")
        self.message_text.insert(tk.END, "\nShort velocity Hz/min: ")
        self.message_text.insert(tk.END, f"{self.plotter.short_diff_data[-1]:.4f}")
        self.message_text.insert(tk.END, "\nLong velocity Hz/min: ")
        self.message_text.insert(tk.END, f"{self.plotter.long_diff_data[-1]:.4f}")
        self.message_text.insert(tk.END, "\n")

        if self.plotter.finish_freq > 0 and self.plotter.short_diff_data:
            self.freq_left = self.plotter.freq_data[-1] - self.plotter.finish_freq
            self.time_left = -(self.plotter.freq_data[-1] - self.plotter.finish_freq) / self.plotter.short_diff_data[-1]
            self.message_text.insert(tk.END, "\nFreq left [Hz]: ")
            self.message_text.insert(tk.END, f"{self.freq_left:.2f}")
            self.message_text.insert(tk.END, "\nTime left [min]: ")
            self.message_text.insert(tk.END, f"{self.time_left:.2f}")
            if self.time_left < 1:
                winsound.Beep(2500, 100)
            if self.time_left < 0:
                winsound.Beep(2500, 1000)

        detail = self.reader.last_error or "Waiting for serial data..."
        self.message_text.insert(tk.END, f"\n{detail}")
        if self.reader.last_raw_response:
            self.message_text.insert(tk.END, f"\nRaw response: {self.reader.last_raw_response}")
        self.status_label.config(text=f"Port: {self.settings.serial.port} | Baudrate: {self.settings.serial.baudrate}")

        time_difference = datetime.now() - current_time
        new_time = int(time_difference.total_seconds() * 1000)
        new_time = 5000 if new_time > 5000 else new_time
        delay_ms = self.settings.app.gate_time_seconds * 1000 - new_time
        self.root.after(max(100, delay_ms), self._refresh_status)

    def exit_app(self) -> None:
        self.reader.close()
        self.root.destroy()

    def _parse_decimal(self, value: str) -> float:
        normalized = value.replace(",", ".")
        return float(normalized)

    def _relative_frequency(self, raw_freq: float) -> float:
        if self.reference_freq is None:
            self.reference_freq = raw_freq
            return 0.0
        return raw_freq - self.reference_freq

    def _resolve_frequency(self, raw_freq: float) -> tuple[float, float]:
        if raw_freq:
            if self.reference_freq is None:
                self.reference_freq = raw_freq
            return raw_freq, self._relative_frequency(raw_freq)

        last_successful = getattr(self.reader, "last_successful_frequency", None)
        if last_successful is not None:
            if self.reference_freq is None:
                self.reference_freq = last_successful
            return last_successful, 0.0

        if self.reference_freq is not None:
            return self.reference_freq, 0.0

        return 0.0, 0.0

    def button_reset(self) -> None:
        self.plotter.clear_plot()
        self.reference_freq = None
        self.message_text.insert(tk.END, "\n======Clear======\n")

    def button_start(self) -> None:
        self.message_text.insert(tk.END, "\n======Start======\n")
        try:
            self.delta_freq = self._parse_decimal(self.input_entry.get())
        except ValueError:
            self.delta_freq = 0.0
        if self.delta_freq is not None:
            self.plotter.finish_line_plot(self.delta_freq)


def create_app(settings_path: Optional[Path] = None) -> QCMApp:
    return QCMApp(settings_path=settings_path)
