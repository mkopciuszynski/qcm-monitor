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
        self.plotter = Plotter(gate_time_seconds=self.settings.app.gate_time_seconds)
        self.delta_freq: Optional[float] = None
        self.time_left: Optional[float] = None
        self.freq_left: Optional[float] = None

        self.root = tk.Tk()
        self.root.title("QCM Monitor")
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
        if raw_freq:
            plotted_freq = raw_freq
            display_freq = raw_freq - self.settings.serial.zero_frequency
        else:
            plotted_freq = 0.0
            display_freq = 0.0
        self.plotter.update_plot(plotted_freq)

        self.message_text.insert(tk.END, "\nRaw freq Hz: ")
        self.message_text.insert(tk.END, f"{raw_freq:.4f}")
        self.message_text.insert(tk.END, "\nDisplay freq Hz: ")
        self.message_text.insert(tk.END, f"{display_freq:.4f}")
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
            if self.time_left < 1:
                winsound.Beep(2500, 100)
            if self.time_left < 0:
                winsound.Beep(2500, 1000)

        detail = self.reader.last_error or "Waiting for serial data..."
        self.message_text.insert(tk.END, f"\n{detail}")
        if self.reader.last_raw_response:
            self.message_text.insert(tk.END, f"\nRaw response: {self.reader.last_raw_response}")
        self.message_text.insert(tk.END, f"\nPort: {self.settings.serial.port}")
        self.message_text.insert(tk.END, f"\nBaudrate: {self.settings.serial.baudrate}")

        time_difference = datetime.now() - current_time
        new_time = int(time_difference.total_seconds() * 1000)
        new_time = 5000 if new_time > 5000 else new_time
        delay_ms = self.settings.app.gate_time_seconds * 1000 - new_time
        self.root.after(max(100, delay_ms), self._refresh_status)

    def exit_app(self) -> None:
        self.reader.close()
        self.root.destroy()

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
