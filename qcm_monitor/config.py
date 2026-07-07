from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SerialSettings:
    port: str = "COM4"
    baudrate: int = 9600
    timeout: float = 1.0
    command: str = "xmt"
    termination: str = "\r"
    zero_frequency: float = 5.97e6
    retries: int = 5
    retry_delay: float = 0.1


@dataclass
class AppSettings:
    gate_time_seconds: int = 5
    window_title: str = "QCM Monitor"
    window_width: int = 700
    window_height: int = 1000
    beep_threshold_minutes: float = 1.0
    beep_duration_ms: int = 100
    beep_warning_ms: int = 1000


@dataclass
class PlotSettings:
    diff_window_points: int = 5
    slope_window_points: int = 50


@dataclass
class Settings:
    serial: SerialSettings
    app: AppSettings
    plot: PlotSettings


DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "settings.ini"


def load_settings(path: Optional[Path] = None) -> Settings:
    config_path = Path(path or DEFAULT_SETTINGS_PATH)
    if not config_path.exists():
        save_settings(Settings(
            serial=SerialSettings(),
            app=AppSettings(),
            plot=PlotSettings(),
        ), config_path)

    parser = configparser.ConfigParser()
    parser.read(config_path)

    serial = SerialSettings(
        port=parser.get("serial", "port", fallback="COM4"),
        baudrate=parser.getint("serial", "baudrate", fallback=9600),
        timeout=parser.getfloat("serial", "timeout", fallback=1.0),
        command=parser.get("serial", "command", fallback="xmt"),
        termination=parser.get("serial", "termination", fallback="\r"),
        zero_frequency=parser.getfloat("serial", "zero_frequency", fallback=5.97e6),
        retries=parser.getint("serial", "retries", fallback=5),
        retry_delay=parser.getfloat("serial", "retry_delay", fallback=0.1),
    )
    app = AppSettings(
        gate_time_seconds=parser.getint("app", "gate_time_seconds", fallback=5),
        window_title=parser.get("app", "window_title", fallback="QCM Monitor"),
        window_width=parser.getint("app", "window_width", fallback=700),
        window_height=parser.getint("app", "window_height", fallback=1000),
        beep_threshold_minutes=parser.getfloat("app", "beep_threshold_minutes", fallback=1.0),
        beep_duration_ms=parser.getint("app", "beep_duration_ms", fallback=100),
        beep_warning_ms=parser.getint("app", "beep_warning_ms", fallback=1000),
    )
    plot = PlotSettings(
        diff_window_points=parser.getint("plot", "diff_window_points", fallback=5),
        slope_window_points=parser.getint("plot", "slope_window_points", fallback=50),
    )
    return Settings(serial=serial, app=app, plot=plot)


def save_settings(settings: Settings, path: Optional[Path] = None) -> Path:
    config_path = Path(path or DEFAULT_SETTINGS_PATH)
    parser = configparser.ConfigParser()
    parser["serial"] = {
        "port": settings.serial.port,
        "baudrate": str(settings.serial.baudrate),
        "timeout": str(settings.serial.timeout),
        "command": settings.serial.command,
        "termination": settings.serial.termination,
        "zero_frequency": str(settings.serial.zero_frequency),
        "retries": str(settings.serial.retries),
        "retry_delay": str(settings.serial.retry_delay),
    }
    parser["app"] = {
        "gate_time_seconds": str(settings.app.gate_time_seconds),
        "window_title": settings.app.window_title,
        "window_width": str(settings.app.window_width),
        "window_height": str(settings.app.window_height),
        "beep_threshold_minutes": str(settings.app.beep_threshold_minutes),
        "beep_duration_ms": str(settings.app.beep_duration_ms),
        "beep_warning_ms": str(settings.app.beep_warning_ms),
    }
    parser["plot"] = {
        "diff_window_points": str(settings.plot.diff_window_points),
        "slope_window_points": str(settings.plot.slope_window_points),
    }
    with config_path.open("w", encoding="utf-8") as handle:
        parser.write(handle)
    return config_path
