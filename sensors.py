"""Sensorfunktionen (DHT22, CPU-Temperatur)."""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime

import adafruit_dht
import board

from config import (
    DHT_PIN,
    MEASUREMENT_RETRIES,
    MEASUREMENT_RETRY_DELAY_SECONDS,
    TIMEZONE,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class SensorReading:
    timestamp: datetime
    temperature_c: float
    humidity_percent: float
    dew_point_c: float


def _calculate_dew_point(temperature_c: float, humidity_percent: float) -> float:
    """Berechnet den Taupunkt in °C (Magnus-Formel)."""
    a = 17.62
    b = 243.12
    gamma = (a * temperature_c / (b + temperature_c)) + math.log(
        humidity_percent / 100.0
    )
    dew_point = (b * gamma) / (a - gamma)
    return round(dew_point, 2)


def _safe_log(value: float, label: str) -> float:
    """Sicheres Logging, falls NaN oder None auftauchen."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Ungültiger Messwert für {label}: {value}")


def read_dht22() -> SensorReading | None:
    """Liest den DHT22 Sensor mit Retries und gibt SensorReading zurück."""
    dht_device = adafruit_dht.DHT22(getattr(board, f"D{DHT_PIN}"))
    try:
        for attempt in range(1, MEASUREMENT_RETRIES + 1):
            try:
                temperature_c = _safe_log(dht_device.temperature, "Temperatur")
                humidity_percent = _safe_log(dht_device.humidity, "Luftfeuchtigkeit")
                dew_point_c = _calculate_dew_point(temperature_c, humidity_percent)
                return SensorReading(
                    timestamp=datetime.now(TIMEZONE),
                    temperature_c=round(temperature_c, 2),
                    humidity_percent=round(humidity_percent, 2),
                    dew_point_c=round(dew_point_c, 2),
                )
            except RuntimeError as exc:
                LOGGER.warning(
                    "DHT22 Lesefehler (Versuch %s/%s): %s",
                    attempt,
                    MEASUREMENT_RETRIES,
                    exc,
                )
                time.sleep(MEASUREMENT_RETRY_DELAY_SECONDS)
            except Exception:
                LOGGER.exception("Unerwarteter DHT22 Fehler")
                time.sleep(MEASUREMENT_RETRY_DELAY_SECONDS)
    finally:
        dht_device.exit()

    LOGGER.error("DHT22 konnte nach %s Versuchen nicht gelesen werden", MEASUREMENT_RETRIES)
    return None


def read_cpu_temperature_c() -> float:
    """Liest die CPU-Temperatur vom Raspberry Pi in °C."""
    with open("/sys/class/thermal/thermal_zone0/temp", "r", encoding="utf-8") as file:
        milli_c = float(file.read().strip())
    return round(milli_c / 1000.0, 2)
