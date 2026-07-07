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
        self.last_raw_response: Optional[str] = None
        self.last_command: Optional[str] = None

    def connect(self) -> bool:
        if self._serial is not None and self._serial.is_open:
            return True
        try:
            self._serial = serial.Serial(
                port=self.settings.port,
                baudrate=self.settings.baudrate,
                timeout=self.settings.timeout,
            )
            self.last_error = None
            return True
        except (serial.SerialException, OSError) as exc:
            self._serial = None
            self.last_error = str(exc)
            return False

    def _is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def close(self) -> None:
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
            self._serial = None

    def read_frequency(self) -> float:
        if not self.connect():
            return 0.0

        if self._serial is None or not self._is_open():
            return 0.0

        for _ in range(5):
            try:
                self.last_command = f"{self.settings.command}{self.settings.termination}"
                self._serial.write(self.last_command.encode("ascii"))
                time.sleep(0.1)
                response = self._serial.read_until(expected=self.settings.termination.encode("ascii"))
                self.last_raw_response = response.decode("ascii", errors="ignore").strip()
                if not response:
                    self.last_error = "No response from device"
                    time.sleep(0.1)
                    continue

                parsed = self._parse_frequency(response)
                if parsed is not None:
                    self.last_error = None
                    return parsed

                self.last_error = f"Could not parse response: {self.last_raw_response}"
            except (serial.SerialException, OSError) as exc:
                self._serial = None
                self.last_error = str(exc)
                return 0.0

        return 0.0

    @staticmethod
    def _parse_frequency(response: bytes) -> Optional[float]:
        text = response.decode("ascii", errors="ignore").strip()
        str_ind = text.find("MHz")
        if str_ind <= 0:
            return None
        return float(text[0:str_ind - 1]) * 10**6
