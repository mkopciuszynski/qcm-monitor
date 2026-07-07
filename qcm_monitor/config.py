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


@dataclass
class AppSettings:
    gate_time_seconds: int = 5
    window_width: int = 600
    window_height: int = 900
    short_velocity_window_points: int = 5
    long_velocity_window_points: int = 20
    beep_threshold_minutes: float = 1.0
    beep_duration_ms: int = 100
    beep_warning_ms: int = 1000


@dataclass
class Settings:
    serial: SerialSettings
    app: AppSettings


DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "settings.ini"
SAMPLE_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "settings.example.ini"


def _decode_escaped_string(value: str) -> str:
    try:
        return bytes(value, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return value


def _encode_escaped_string(value: str) -> str:
    return value.encode("unicode_escape").decode("ascii")


def load_settings(path: Optional[Path] = None) -> Settings:
    config_path = Path(path or DEFAULT_SETTINGS_PATH)
    if not config_path.exists():
        if SAMPLE_SETTINGS_PATH.exists():
            config_path = SAMPLE_SETTINGS_PATH
        else:
            save_settings(Settings(
                serial=SerialSettings(),
                app=AppSettings(),
            ), config_path)
            return load_settings(config_path)

    parser = configparser.ConfigParser()
    parser.read(config_path)

    serial = SerialSettings(
        port=parser.get("serial", "port", fallback="COM4"),
        baudrate=parser.getint("serial", "baudrate", fallback=9600),
        timeout=parser.getfloat("serial", "timeout", fallback=1.0),
        command=_decode_escaped_string(parser.get("serial", "command", fallback="xmt")),
        termination=_decode_escaped_string(parser.get("serial", "termination", fallback="\r")),
    )
    app = AppSettings(
        gate_time_seconds=parser.getint("app", "gate_time_seconds", fallback=5),
        window_width=parser.getint("app", "window_width", fallback=600),
        window_height=parser.getint("app", "window_height", fallback=900),
        short_velocity_window_points=parser.getint("app", "short_velocity_window_points", fallback=5),
        long_velocity_window_points=parser.getint("app", "long_velocity_window_points", fallback=20),
        beep_threshold_minutes=parser.getfloat("app", "beep_threshold_minutes", fallback=1.0),
        beep_duration_ms=parser.getint("app", "beep_duration_ms", fallback=100),
        beep_warning_ms=parser.getint("app", "beep_warning_ms", fallback=1000),
    )
    return Settings(serial=serial, app=app)


def save_settings(settings: Settings, path: Optional[Path] = None) -> Path:
    config_path = Path(path or DEFAULT_SETTINGS_PATH)
    parser = configparser.ConfigParser()
    parser["serial"] = {
        "port": settings.serial.port,
        "baudrate": str(settings.serial.baudrate),
        "timeout": str(settings.serial.timeout),
        "command": _encode_escaped_string(settings.serial.command),
        "termination": _encode_escaped_string(settings.serial.termination),
    }
    parser["app"] = {
        "gate_time_seconds": str(settings.app.gate_time_seconds),
        "window_width": str(settings.app.window_width),
        "window_height": str(settings.app.window_height),
        "short_velocity_window_points": str(settings.app.short_velocity_window_points),
        "long_velocity_window_points": str(settings.app.long_velocity_window_points),
        "beep_threshold_minutes": str(settings.app.beep_threshold_minutes),
        "beep_duration_ms": str(settings.app.beep_duration_ms),
        "beep_warning_ms": str(settings.app.beep_warning_ms),
    }
    with config_path.open("w", encoding="utf-8") as handle:
        parser.write(handle)
    return config_path
