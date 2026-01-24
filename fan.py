"""Lüftersteuerung per GPIO mit Hysterese."""
from __future__ import annotations

import logging
import time

import RPi.GPIO as GPIO

from config import CPU_TEMP_CHECK_SECONDS, CPU_TEMP_OFF_C, CPU_TEMP_ON_C, FAN_PIN
from sensors import read_cpu_temperature_c

LOGGER = logging.getLogger(__name__)


class FanController:
    """Steuert einen Lüfter mit sicherem Start-/Stopp-Zustand."""

    def __init__(self) -> None:
        self._is_on = False
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(FAN_PIN, GPIO.OUT, initial=GPIO.LOW)

    def cleanup(self) -> None:
        """Setzt den Lüfter auf AUS und räumt GPIO auf."""
        self.set_fan(False)
        GPIO.cleanup()

    def set_fan(self, enabled: bool) -> None:
        """Schaltet den Lüfter und loggt Statusänderungen."""
        if enabled == self._is_on:
            return
        GPIO.output(FAN_PIN, GPIO.HIGH if enabled else GPIO.LOW)
        self._is_on = enabled
        LOGGER.info(
            "Lüfter %s (CPU %.2f °C)",
            "EIN" if enabled else "AUS",
            read_cpu_temperature_c(),
        )

    def run_loop(self, stop_event) -> None:
        """Prüft die CPU-Temperatur und steuert den Lüfter."""
        while not stop_event.is_set():
            try:
                cpu_temp = read_cpu_temperature_c()
                if cpu_temp >= CPU_TEMP_ON_C:
                    self.set_fan(True)
                elif cpu_temp <= CPU_TEMP_OFF_C:
                    self.set_fan(False)
            except Exception:
                LOGGER.exception("Fehler beim Lesen der CPU-Temperatur")
            stop_event.wait(CPU_TEMP_CHECK_SECONDS)
