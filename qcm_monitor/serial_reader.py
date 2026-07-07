from __future__ import annotations

import re
import time
from typing import Optional

import serial

from .config import SerialSettings


class SerialFrequencyReader:
    """Read frequency values from a serial device."""

    def __init__(self, settings: SerialSettings) -> None:
        self.settings = settings
        self._serial: Optional[serial.Serial] = None
        self.last_error: Optional[str] = None

    def connect(self) -> bool:
        if self._serial is not None and self._serial.is_open:
            return True
        try:
            self._serial = serial.Serial(
                port=self.settings.port,
                baudrate=self.settings.baudrate,
                timeout=min(self.settings.timeout, 0.2),
            )
            self.last_error = None
            return True
        except (serial.SerialException, OSError) as exc:
            self._serial = None
            self.last_error = str(exc)
            return False

    def close(self) -> None:
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
            self._serial = None

    def read_frequency(self) -> float:
        if not self.connect():
            return 0.0

        if self._serial is None or not self._serial.is_open:
            return 0.0

        try:
            self._serial.write(f"{self.settings.command}{self.settings.termination}".encode("ascii"))
            self._serial.flushInput()
            response = self._serial.read_until(expected=self.settings.termination.encode("ascii"))
            if not response:
                return 0.0
            parsed = self._parse_frequency(response)
            if parsed is not None:
                return parsed
        except (serial.SerialException, OSError) as exc:
            self._serial = None
            self.last_error = str(exc)
            return 0.0
        return 0.0

    @staticmethod
    def _parse_frequency(response: bytes) -> Optional[float]:
        text = response.decode("ascii", errors="ignore").strip()
        match = re.search(r"([0-9.]+)\s*MHz", text)
        if not match:
            return None
        return float(match.group(1)) * 10**6
