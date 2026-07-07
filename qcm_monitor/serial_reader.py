from __future__ import annotations

import re
import sys
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
            print(f"[serial] already open on {self.settings.port}")
            return True
        try:
            print(f"[serial] opening {self.settings.port} @ {self.settings.baudrate} baud")
            self._serial = serial.Serial(
                port=self.settings.port,
                baudrate=self.settings.baudrate,
                timeout=self.settings.timeout,
            )
            print(f"[serial] opened successfully: {self._serial}")
            self.last_error = None
            return True
        except (serial.SerialException, OSError) as exc:
            self._serial = None
            self.last_error = str(exc)
            print(f"[serial] connection failed: {exc}")
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

        for attempt in range(5):
            try:
                self.last_command = f"{self.settings.command}{self.settings.termination}"
                print(f"[serial] attempt {attempt + 1}: sending {self.last_command!r}")
                self._serial.write(self.last_command.encode("ascii"))
                time.sleep(0.1)
                response = self._serial.read_until(expected=self.settings.termination.encode("ascii"))
                self.last_raw_response = response.decode("ascii", errors="ignore").strip()
                print(f"[serial] attempt {attempt + 1}: raw response {self.last_raw_response!r}")
                if not response:
                    self.last_error = "No response from device"
                    print("[serial] no response received")
                    time.sleep(0.1)
                    continue

                parsed = self._parse_frequency(response)
                if parsed is not None:
                    self.last_error = None
                    print(f"[serial] parsed frequency: {parsed}")
                    return parsed

                self.last_error = f"Could not parse response: {self.last_raw_response}"
                print(f"[serial] parse failed: {self.last_error}")
            except (serial.SerialException, OSError) as exc:
                self._serial = None
                self.last_error = str(exc)
                print(f"[serial] read error: {exc}")
                return 0.0

        return 0.0

    @staticmethod
    def _parse_frequency(response: bytes) -> Optional[float]:
        text = response.decode("ascii", errors="ignore").strip()
        str_ind = text.find("MHz")
        if str_ind <= 0:
            return None
        return float(text[0:str_ind - 1]) * 10**6
