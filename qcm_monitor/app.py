from __future__ import annotations

import tkinter as tk
import winsound
from datetime import datetime
from pathlib import Path
from typing import Optional
import matplotlib as mpl

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .config import load_settings
from .plotter import Plotter
from .serial_reader import SerialFrequencyReader


class QCMApp:
    """Main application window for QCM monitoring."""

    def __init__(self, settings_path: Optional[Path] = None) -> None:
        self.settings = load_settings(settings_path)
        self.reader = SerialFrequencyReader(self.settings.serial)
        
        # --- 1. SET MATPLOTLIB DARK STYLE BEFORE INITIALIZING PLOTTER ---
        
        mpl.rcParams['figure.facecolor'] = '#1e1e1e'
        mpl.rcParams['axes.facecolor'] = '#1e1e1e'
        mpl.rcParams['axes.edgecolor'] = '#ffffff'
        mpl.rcParams['axes.labelcolor'] = '#ffffff'
        mpl.rcParams['xtick.color'] = '#ffffff'
        mpl.rcParams['ytick.color'] = '#ffffff'
        mpl.rcParams['grid.color'] = '#444444'
        mpl.rcParams['text.color'] = '#ffffff'

        self.plotter = Plotter(
            short_diff_window_points=self.settings.app.short_slope_window_points,
            average_diff_window_points=self.settings.app.average_slope_window_points,
            long_diff_window_points=self.settings.app.long_slope_window_points,
            gate_time_seconds=self.settings.app.gate_time_seconds,
        )
        self.delta_freq: Optional[float] = None
        self.time_left: Optional[float] = None
        self.freq_left: Optional[float] = None
        self.reference_freq: Optional[float] = None
        self.last_beep_time: Optional[datetime] = None
        self.started_deposition = False

        # --- 2. DEFINE DARK PALETTE ---
        BG_COLOR = "#1e1e1e"      # Dark grey window background
        WIDGET_BG = "#2d2d2d"     # Slightly lighter grey for entry/text/buttons
        TEXT_COLOR = "#ffffff"    # White text
        BTN_BG = "#3e3e3e"        # Grey button background

        self.root = tk.Tk()
        self.root.title("QCM Monitor")
        self.root.configure(bg=BG_COLOR)  # Make main window dark
        self.root.geometry(f"{self.settings.app.window_width}x{self.settings.app.window_height}+0+0")
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # Apply dark background to frames
        self.main_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.plot_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.plot_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = FigureCanvasTkAgg(self.plotter.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.bottom_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # --- 3. STYLE TEXT BOX AND INPUTS ---
        self.message_text = tk.Text(
            self.bottom_frame, height=14, width=40, 
            bg=WIDGET_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=0
        )
        self.message_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.button_frame = tk.Frame(self.bottom_frame, bg=BG_COLOR)
        self.button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))

        self.input_entry = tk.Entry(
            self.button_frame, width=10, 
            bg=WIDGET_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=1
        )
        self.start_button = tk.Button(self.button_frame, text="Start", width=8, command=self.button_start, bg=BTN_BG, fg=TEXT_COLOR, activebackground=WIDGET_BG, activeforeground=TEXT_COLOR)
        self.reset_button = tk.Button(self.button_frame, text="Clear", width=8, command=self.button_reset, bg=BTN_BG, fg=TEXT_COLOR, activebackground=WIDGET_BG, activeforeground=TEXT_COLOR)
        self.exit_button = tk.Button(self.button_frame, text="Exit", width=8, command=self.exit_app, bg=BTN_BG, fg=TEXT_COLOR, activebackground=WIDGET_BG, activeforeground=TEXT_COLOR)

        self.input_entry.grid(row=0, column=0, padx=2, pady=3)
        self.start_button.grid(row=0, column=1, padx=2, pady=3)
        self.reset_button.grid(row=1, column=0, padx=2, pady=3)
        self.exit_button.grid(row=1, column=1, padx=2, pady=3)

        self.status_label = tk.Label(self.root, text="", anchor=tk.W, bg=BG_COLOR, fg=TEXT_COLOR)
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
        self.message_text.insert(tk.END, "\nRelative freq Hz: ")
        self.message_text.insert(tk.END, f"{display_freq:.4f}")
        
        avg_slope = self.plotter.average_diff_data[-1] if self.plotter.average_diff_data else 0.0
        long_slope = self.plotter.long_diff_data[-1] if self.plotter.long_diff_data else 0.0
        
        self.message_text.insert(tk.END, f"\nSlope ({self.settings.app.average_slope_window_points} pts) Hz/min: ")
        self.message_text.insert(tk.END, f"{avg_slope:.4f}")
        self.message_text.insert(tk.END, f"\nLong slope ({self.settings.app.long_slope_window_points} pts) Hz/min: ")
        self.message_text.insert(tk.END, f"{long_slope:.4f}")
        self.message_text.insert(tk.END, "\n")

        # ALWAYS show deposition variables immediately if deposition mode is engaged
        if self.started_deposition:
            finish_freq = getattr(self.plotter, "finish_freq", 0)
            
            if self.plotter.freq_data:
                self.freq_left = abs(self.plotter.freq_data[-1] - finish_freq)
            else:
                # Fallback calculation if array hasn't filled yet
                self.freq_left = abs(display_freq - finish_freq)

            if avg_slope not in (None, float("nan")) and avg_slope != 0:
                self.time_left = self.freq_left / abs(avg_slope)
            else:
                self.time_left = None
                
            self.message_text.insert(tk.END, "\nHz left: ")
            self.message_text.insert(tk.END, f"{self.freq_left:.2f}")
            self.message_text.insert(tk.END, "\nMin left: ")
            self.message_text.insert(tk.END, f"{self.time_left:.2f}" if self.time_left is not None else "Calculating...")
            
            # Isolated audio warning triggers
            if self.time_left is not None:
                if self.time_left < 1:
                    if self.last_beep_time is None or (current_time - self.last_beep_time).total_seconds() >= self.settings.app.beep_every_seconds:
                        winsound.Beep(2500, self.settings.app.beep_duration_ms)
                        self.last_beep_time = current_time
                if self.time_left < 0:
                    winsound.Beep(2500, self.settings.app.beep_warning_ms)

        detail = self.reader.last_error or ""
        if detail:
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
        self.delta_freq = None
        self.freq_left = None
        self.time_left = None
        self.started_deposition = False
        self.last_beep_time = None
        self.message_text.delete(1.0, tk.END)
        self.message_text.insert(tk.END, "\n======Clear======\n")

    def button_start(self) -> None:
        try:
            self.delta_freq = self._parse_decimal(self.input_entry.get())
        except ValueError:
            self.delta_freq = 0.0
            
        if self.delta_freq is not None:
            self.plotter.finish_line_plot(self.delta_freq)
            self.started_deposition = True
            self.last_beep_time = None
            if self.plotter.freq_data:
                start_freq = self.plotter.freq_data[-1]
                self.message_text.insert(tk.END, f"\nStart freq (real): {start_freq:.4f} Hz\n")
                if self.plotter.average_diff_data and self.plotter.average_diff_data[-1] not in (None, float("nan")) and self.plotter.average_diff_data[-1] != 0:
                    slope = self.plotter.average_diff_data[-1]
                    remaining_time = -(self.plotter.finish_freq - start_freq) / slope
                    remaining_hz = self.plotter.finish_freq - start_freq
                    self.message_text.insert(tk.END, f"Hz left: {remaining_hz:.4f}\n")
                    self.message_text.insert(tk.END, f"Min left: {remaining_time:.4f}\n")


def create_app(settings_path: Optional[Path] = None) -> QCMApp:
    return QCMApp(settings_path=settings_path)
