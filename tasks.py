"""Hintergrundaufgaben für Messungen und Lüftersteuerung."""
from __future__ import annotations

import logging
import threading
import time

from config import MEASUREMENT_INTERVAL_SECONDS
from db import insert_measurement
from sensors import read_dht22

LOGGER = logging.getLogger(__name__)


def measurement_loop(stop_event: threading.Event) -> None:
    """Liest regelmäßig den DHT22 Sensor und speichert Messungen."""
    while not stop_event.is_set():
        reading = None
        try:
            reading = read_dht22()
        except Exception:
            LOGGER.exception("Fehler beim Lesen des DHT22 Sensors")

        if reading:
            try:
                insert_measurement(
                    reading.timestamp,
                    reading.temperature_c,
                    reading.humidity_percent,
                    reading.dew_point_c,
                )
            except Exception:
                LOGGER.exception("Fehler beim Schreiben in die Datenbank")
        else:
            LOGGER.error("Keine Messung gespeichert (Sensorfehler)")

        stop_event.wait(MEASUREMENT_INTERVAL_SECONDS)
