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
        # Read setting and init Serial Reader
        self.settings = load_settings(settings_path)

        self.reader = SerialFrequencyReader(self.settings.serial)
        if self.reader.connect():
            print("[app] Serial device connected successfully.")
        else:
            print(f"[app] Warning: Could not connect to serial device: {self.reader.last_error}")

        # --- 1. SET MATPLOTLIB DARK STYLE BEFORE INITIALIZING PLOTTER ---
        mpl.rcParams['figure.facecolor'] = '#1e1e1e'
        mpl.rcParams['axes.facecolor'] = '#1e1e1e'
        mpl.rcParams['axes.edgecolor'] = '#ffffff'
        mpl.rcParams['axes.labelcolor'] = '#ffffff'
        mpl.rcParams['xtick.color'] = '#ffffff'
        mpl.rcParams['ytick.color'] = '#ffffff'
        mpl.rcParams['grid.color'] = '#444444'
        mpl.rcParams['text.color'] = '#ffffff'

        # Small font rules:
        mpl.rcParams['font.size'] = 10          
        mpl.rcParams['axes.labelsize'] = 10     
        mpl.rcParams['xtick.labelsize'] = 9    
        mpl.rcParams['ytick.labelsize'] = 9

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
        self.last_freq: Optional[float] = None

        # --- 2. DEFINE DARK PALETTE ---
        BG_COLOR = "#1e1e1e"      # Dark grey window background
        WIDGET_BG = "#2d2d2d"     # Slightly lighter grey for fields/buttons
        TEXT_COLOR = "#ffffff"    # White text
        BTN_BG = "#3e3e3e"        # Grey button background
        ACCENT_COLOR = "#00ffcc"  # Teal highlight for live telemetry numbers

        self.root = tk.Tk()
        self.root.title("QCM Monitor")
        self.root.configure(bg=BG_COLOR)
        
        # Enforce exact width and height
        self.root.geometry("600x950+0+0")
        self.root.resizable(False, False) 
        self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

        # --- STATUS BAR ---
        self.status_bar = tk.Label(
            self.root,
            text="Port: N/A | Baudrate: N/A | Last Raw: None | Last Read: N/A",
            bd=1,
            relief=tk.SUNKEN,
            anchor=tk.CENTER,
            bg=WIDGET_BG,
            fg=TEXT_COLOR,
            font=("Courier", 10)
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.main_frame = tk.Frame(self.root, bg=BG_COLOR)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- 3. HARD CONSTRAIN PLOT FRAME (600x600 px) ---
        self.plot_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.plot_frame.pack(fill=tk.X, expand=False) 

        self.canvas = FigureCanvasTkAgg(self.plotter.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- 4. BOTTOM FRAME FOR CONTROLS & DASHBOARD ---
        self.bottom_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # --- TELEMETRY DASHBOARD PANEL ---
        self.dashboard_frame = tk.Frame(self.bottom_frame, bg=BG_COLOR)
        self.dashboard_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.telemetry_vars = {
            "rel_freq": tk.StringVar(value="0.0000"),
            "slope": tk.StringVar(value="0.0000"),
            "long_slope": tk.StringVar(value="0.0000"),
            "hz_stop": tk.StringVar(value="Waiting"),
            "hz_left": tk.StringVar(value="Waiting"),
            "min_left": tk.StringVar(value="Waiting"),
        }

        labels_text = [
            ("Relative Freq (Hz):", "rel_freq"),
            ("Slope (Hz/min):", "slope"),
            ("Slope averaged (Hz/min):", "long_slope"),
            ("Hz stop:", "hz_stop"),
            ("Hz Left:", "hz_left"),
            ("Min Left:", "min_left"),
        ]

        for idx, (label_txt, var_key) in enumerate(labels_text):
            lbl = tk.Label(self.dashboard_frame, text=label_txt, bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.W, font=("Arial", 10, "bold"))
            lbl.grid(row=idx, column=0, sticky=tk.W, padx=10, pady=6)
            
            entry = tk.Entry(
                self.dashboard_frame, textvariable=self.telemetry_vars[var_key], 
                width=18, bg=WIDGET_BG, fg=ACCENT_COLOR, readonlybackground=WIDGET_BG,
                font=("Courier", 11, "bold"), state="readonly", bd=1, relief=tk.SOLID
            )
            entry.grid(row=idx, column=1, sticky=tk.W, padx=15, pady=6)

        # --- RIGHT-SIDE CONTROL BUTTONS FRAME ---
        self.button_frame = tk.Frame(self.bottom_frame, bg=BG_COLOR)
        self.button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 15))

        self.entry_label = tk.Label(self.button_frame, text="Target ΔF (Hz):", bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.W, font=("Arial", 10, "bold"))
        
        # --- STYLED TO MATCH THE TELEMETRY ENTRIES ---
        self.input_entry = tk.Entry(
            self.button_frame, 
            width=12, 
            bg=WIDGET_BG, 
            fg=ACCENT_COLOR,                # Text changes to matching accent color when typing
            insertbackground=ACCENT_COLOR,  # Flashing cursor matches theme color accent
            disabledbackground=WIDGET_BG,   # Locked state keeps consistency
            font=("Courier", 10, "bold"),   # Matching typography
            bd=1, 
            relief=tk.SOLID                 # Matching flat borders
        )
        
        # Bind Enter Key
        self.input_entry.bind("<Return>", lambda event: self.button_start())

        self.start_button = tk.Button(self.button_frame, text="Start", width=10, command=self.button_start, bg=BTN_BG, fg=TEXT_COLOR, activebackground=WIDGET_BG, activeforeground=TEXT_COLOR)
        self.reset_button = tk.Button(self.button_frame, text="Reset", width=10, command=self.button_reset, bg=BTN_BG, fg=TEXT_COLOR, activebackground=WIDGET_BG, activeforeground=TEXT_COLOR)
        self.exit_button = tk.Button(self.button_frame, text="Exit", width=10, command=self.exit_app, bg=BTN_BG, fg=TEXT_COLOR, activebackground=WIDGET_BG, activeforeground=TEXT_COLOR)

        self.entry_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(4, 2), padx=2)
        self.input_entry.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 14), padx=2, ipady=1) # ipady slightly balances the entry frame size
        self.start_button.grid(row=2, column=0, padx=2, pady=4)
        self.reset_button.grid(row=2, column=1, padx=2, pady=4)
        self.exit_button.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(10, 0))

        self.root.after(100, self._refresh_status)

    def run(self) -> None:
        self.root.mainloop()

    def _refresh_status(self) -> None:
        current_time = datetime.now()

        print(f"[app] refresh cycle at {current_time.strftime('%H:%M:%S')}")
        raw_freq = self.reader.read_frequency()
        plotted_freq, display_freq = self._resolve_frequency(raw_freq)
        self.plotter.update_plot(display_freq)

        # Update status bar metrics dynamically
        port = getattr(self.settings.serial, 'port', 'N/A')
        baudrate = getattr(self.settings.serial, 'baudrate', 'N/A')
        raw_resp = self.reader.last_raw_response.strip() if self.reader.last_raw_response else "None"
        read_time = current_time.strftime("%H:%M:%S")
        self.status_bar.config(
            text=f" {port} | {baudrate} \t\t\t Last Read: {read_time} | {raw_resp}"
        )

        # Update Dashboard Fields instead of text panel
        self.telemetry_vars["rel_freq"].set(f"{display_freq:.4f}")
        
        avg_slope = self.plotter.average_diff_data[-1] if self.plotter.average_diff_data else 0.0
        long_slope = self.plotter.long_diff_data[-1] if self.plotter.long_diff_data else 0.0
        
        self.telemetry_vars["slope"].set(f"{avg_slope:.4f}")
        self.telemetry_vars["long_slope"].set(f"{long_slope:.4f}")

        if self.started_deposition:
            finish_freq = getattr(self.plotter, "finish_freq", 0)
            
            if self.plotter.freq_data:
                self.freq_left = self.plotter.freq_data[-1] - finish_freq
            else:
                self.freq_left = display_freq - finish_freq

            if avg_slope not in (None, float("nan")) and abs(avg_slope) > 0.0001:
                self.time_left = self.freq_left / abs(avg_slope)
            else:
                self.time_left = None

            hz_stop = (self.reference_freq + finish_freq) / 10 ** 6
            self.telemetry_vars["hz_stop"].set(f"{hz_stop:.8f}")
            self.telemetry_vars["hz_left"].set(f"{self.freq_left:.2f}")
            self.telemetry_vars["min_left"].set(f"{self.time_left:.2f}" if self.time_left is not None else "Calculating...")
            
            if self.time_left is not None:
                if self.time_left < 1:
                    if self.last_beep_time is None or (current_time - self.last_beep_time).total_seconds() >= self.settings.app.beep_every_seconds:
                        winsound.Beep(2500, self.settings.app.beep_duration_ms)
                        self.last_beep_time = current_time
                if self.time_left < 0:
                    winsound.Beep(2500, self.settings.app.beep_warning_ms)
        else:
            self.telemetry_vars["hz_left"].set("waiting")
            self.telemetry_vars["min_left"].set("waiting")
            self.telemetry_vars["hz_stop"].set("waiting")

        # 1. Calculate execution loop cycle time
        time_difference = datetime.now() - current_time
        execution_ms = int(time_difference.total_seconds() * 1000)
        
        # 2. Convert gate time to milliseconds
        gate_ms = int(self.settings.app.gate_time_seconds * 1000)
        
        # 3. Target delay calculation
        delay_ms = max(100, gate_ms - execution_ms)
        
        self.root.after(delay_ms, self._refresh_status)

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
            self.last_freq = raw_freq
            if self.reference_freq is None:
                self.reference_freq = raw_freq
            return raw_freq, self._relative_frequency(raw_freq)

        last_successful = getattr(self.reader, "last_successful_frequency", None)
        if last_successful is not None:
            self.last_freq = last_successful
            if self.reference_freq is None:
                self.reference_freq = last_successful
            return last_successful, 0.0

        if self.reference_freq is not None:
            return self.reference_freq, 0.0

        return 0.0, 0.0

    def button_reset(self) -> None:
        self.input_entry.config(state="normal")
        self.input_entry.delete(0, tk.END) 
        
        self.plotter.clear_plot()
        self.reference_freq = None
        self.delta_freq = None
        self.freq_left = None
        self.time_left = None
        self.started_deposition = False
        self.last_beep_time = None
        self.last_freq = None
        
        # Reset telemetry numbers to default states
        self.telemetry_vars["rel_freq"].set("0.0000")
        self.telemetry_vars["slope"].set("0.0000")
        self.telemetry_vars["long_slope"].set("0.0000")
        self.telemetry_vars["hz_stop"].set("waiting")
        self.telemetry_vars["hz_left"].set("waiting")
        self.telemetry_vars["min_left"].set("waiting")

        # --- RESTORE START BUTTON TO NORMAL ---
        self.start_button.config(
            relief=tk.RAISED, 
            bg="#3e3e3e",       # Original BTN_BG color
            state="normal"      # Re-enable interactivity
        )

    def button_start(self) -> None:
        try:
            self.delta_freq = self._parse_decimal(self.input_entry.get())
            self.input_entry.config(state="disabled")
        except ValueError:
            self.delta_freq = 0.0
            
        if self.delta_freq is not None:
            self.plotter.finish_line_plot(self.delta_freq)
            self.started_deposition = True
            self.last_beep_time = None
            if self.plotter.freq_data:
                start_freq = self.plotter.freq_data[-1]
                
                if self.plotter.average_diff_data and self.plotter.average_diff_data[-1] not in (None, float("nan")) and self.plotter.average_diff_data[-1] != 0:
                    slope = self.plotter.average_diff_data[-1]
                    remaining_time = -(self.plotter.finish_freq - start_freq) / slope
                    remaining_hz = self.plotter.finish_freq - start_freq

        self.start_button.config(
            relief=tk.SUNKEN, 
            bg="#2d2d2d",       # Darker background to look deflated/inactive
            state="disabled",   # Prevents accidental double clicks
            disabledforeground="#FF0000" # Dimmed text color while pressed
        )


def create_app(settings_path: Optional[Path] = None) -> QCMApp:
    return QCMApp(settings_path=settings_path)