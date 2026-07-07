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

    def connect(self) -> None:
        if self._serial is not None and self._serial.is_open:
            return
        self._serial = serial.Serial(
            port=self.settings.port,
            baudrate=self.settings.baudrate,
            timeout=self.settings.timeout,
        )

    def close(self) -> None:
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
            self._serial = None

    def read_frequency(self) -> float:
        self.connect()
        if self._serial is None or not self._serial.is_open:
            return 0.0

        try:
            self._serial.write(f"{self.settings.command}{self.settings.termination}".encode("ascii"))
            time.sleep(0.1)
            response = self._serial.read_until(expected=self.settings.termination.encode("ascii"))
            if not response:
                return 0.0
            parsed = self._parse_frequency(response)
            if parsed is not None:
                return parsed
        except Exception:
            return 0.0
        return 0.0

    @staticmethod
    def _parse_frequency(response: bytes) -> Optional[float]:
        text = response.decode("ascii", errors="ignore").strip()
        match = re.search(r"([0-9.]+)\s*MHz", text)
        if not match:
            return None
        return float(match.group(1)) * 10**6
