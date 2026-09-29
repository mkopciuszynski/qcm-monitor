from __future__ import annotations

import time
from typing import Optional

import serial
from .config import SerialSettings


class SerialFrequencyReader:
    """Read frequency values from a serial device."""

    def __init__(self, settings: SerialSettings) -> None:
        self.settings = settings
        self.last_error: Optional[str] = None
        self.last_raw_response: Optional[str] = None
        self.last_frequency: Optional[float] = None

        self._serial: Optional[serial.Serial] = None
        self._command = f"{self.settings.command}{self.settings.termination}".encode("ascii")

    def connect(self) -> bool:
        if self._serial and self._serial.is_open:
            print(f"[serial] already open on {self.settings.port}")
            return True
        try:
            print(f"[serial] opening {self.settings.port} @ {self.settings.baudrate} baud")
            self._serial = serial.Serial(
                port=self.settings.port,
                baudrate=self.settings.baudrate,
                timeout=self.settings.timeout,
            )
            self.last_error = None
            print(f"[serial] opened successfully: {self._serial}")
            return True
        except (serial.SerialException, OSError) as exc:
            self._serial, self.last_error = None, str(exc)
            print(f"[serial] connection failed: {exc}")
            return False

    def close(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    def read_frequency(self) -> float:
        if not self._serial:
            return 0.0

        termination_bytes = self.settings.termination.encode("ascii")

        for attempt in range(5):
            try:
                self._serial.write(self._command)
                time.sleep(0.1)
                
                raw_response = self._serial.read_until(expected=termination_bytes)
                if not raw_response:
                    self.last_error = "No response from device"
                    print("[serial] no response received")
                    time.sleep(0.1)
                    continue

                self.last_raw_response = raw_response.decode("ascii", errors="ignore").strip()
                print(f"[serial] attempt {attempt + 1}: raw response {self.last_raw_response!r}")

                parsed = self._parse_frequency(self.last_raw_response)
                if parsed is not None:
                    self.last_error = None
                    self.last_frequency = parsed
                    print(f"[serial] parsed frequency: {parsed}")
                    return parsed

                self.last_error = f"Could not parse response: {self.last_raw_response}"
                print(f"[serial] parse failed: {self.last_error}")

            except (serial.SerialException, OSError) as exc:
                self._serial, self.last_error = None, str(exc)
                print(f"[serial] read error: {exc}")
                return 0.0

        return 0.0

    @staticmethod
    def _parse_frequency(text: str) -> Optional[float]:
        if "MHz" not in text:
            return None
        try:
            numeric_part = text.split("MHz")[0].strip()
            return float(numeric_part) * 10**6
        except ValueError:
            return None