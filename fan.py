"""Lüftersteuerung per GPIO mit Hysterese."""
from __future__ import annotations

import logging
import time

import board
import digitalio

from config import CPU_TEMP_CHECK_SECONDS, CPU_TEMP_OFF_C, CPU_TEMP_ON_C, FAN_PIN
from sensors import read_cpu_temperature_c

LOGGER = logging.getLogger(__name__)


class FanController:
    """Steuert einen Lüfter mit sicherem Start-/Stopp-Zustand."""

    def __init__(self) -> None:
        self._is_on = False
        self._pin = digitalio.DigitalInOut(getattr(board, f"D{FAN_PIN}"))
        self._pin.direction = digitalio.Direction.OUTPUT
        self._pin.value = False

    def cleanup(self) -> None:
        """Setzt den Lüfter auf AUS und räumt GPIO auf."""
        self.set_fan(False)
        self._pin.deinit()

    def set_fan(self, enabled: bool) -> None:
        """Schaltet den Lüfter und loggt Statusänderungen."""
        if enabled == self._is_on:
            return
        self._pin.value = enabled
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
