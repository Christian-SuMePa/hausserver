"""Zentrale Konfiguration für den Hausserver.

Alle Zeitstempel werden in lokaler Zeit gespeichert. Verbindliche Zeitzone: Europe/Berlin.
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

# Zeitzone für Speicherung und Anzeige
TIMEZONE = ZoneInfo("Europe/Berlin")

# Datenbank
DB_PATH = "/var/lib/hausserver/hausserver.db"
DB_TIMEOUT_SECONDS = 10

# Sensor / Messungen
DHT_PIN = 23
MEASUREMENT_INTERVAL_SECONDS = 15 * 60
MEASUREMENT_RETRIES = 3
MEASUREMENT_RETRY_DELAY_SECONDS = 2

# Lüftersteuerung
FAN_PIN = 4
CPU_TEMP_ON_C = 69.0
CPU_TEMP_OFF_C = 65.0
CPU_TEMP_CHECK_SECONDS = 60

# Datenaufbewahrung (6 Monate)
DATA_RETENTION_MONTHS = 6

# Glättung für Dach-Chart
SMOOTHING_WINDOW = 4

# Wetter (DWD OpenData)
DWD_STATION_ID = "10433"  # Rheinstetten (MOSMIX Station, ggf. anpassen)
DWD_WARNING_AREA = "Rheinstetten"
WEATHER_CACHE_MINUTES = 60

# Server
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000

# Logging
LOG_PATH = "/var/log/hausserver/hausserver.log"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3
