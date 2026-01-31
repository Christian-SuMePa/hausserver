"""Wetterdaten über DWD OpenData."""
from __future__ import annotations

import logging
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from zipfile import ZipFile

from config import DWD_STATION_ID, DWD_WARNING_AREA, TIMEZONE, WEATHER_CACHE_MINUTES

LOGGER = logging.getLogger(__name__)

MOSMIX_URL = (
    "https://opendata.dwd.de/weather/local_forecasts/mos/"
    "MOSMIX_L/single_stations/{station}/kml/MOSMIX_L_LATEST_{station}.kmz"
)

WARNINGS_BASE_URL = (
    "https://opendata.dwd.de/weather/alerts/cap/COMMUNEUNION_DWD_STAT/"
)


@dataclass
class WeatherData:
    updated_at: datetime
    hourly: list[dict]
    today_summary: dict
    warnings: list[dict]


class WeatherCache:
    """Einfacher In-Memory-Cache für Wetterdaten."""

    def __init__(self) -> None:
        self._timestamp = 0.0
        self._data: WeatherData | None = None

    def get(self) -> WeatherData | None:
        return self._data

    def is_valid(self) -> bool:
        return (time.time() - self._timestamp) < WEATHER_CACHE_MINUTES * 60

    def set(self, data: WeatherData) -> None:
        self._data = data
        self._timestamp = time.time()


WEATHER_CACHE = WeatherCache()


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read()


def _download_text(url: str) -> str:
    return _download(url).decode("utf-8", errors="ignore")


def _extract_kml_from_kmz(kmz_bytes: bytes) -> bytes:
    with ZipFile(BytesIO(kmz_bytes)) as zf:
        for name in zf.namelist():
            if name.lower().endswith(".kml"):
                return zf.read(name)
    raise ValueError("KMZ enthält keine KML-Datei")


def _parse_mosmix(kml_bytes: bytes) -> tuple[list[dict], dict]:
    """Parst MOSMIX KML für die gewählte Station."""
    tree = ET.fromstring(kml_bytes)

    def local_name(tag: str) -> str:
        return tag.split("}", 1)[-1] if "}" in tag else tag

    def find_value_text(node: ET.Element) -> str:
        for child in node:
            if local_name(child.tag) == "value":
                return child.text or ""
        return ""

    timesteps: list[datetime] = []
    for ts in tree.findall(".//{*}TimeStep"):
        if ts.text:
            timesteps.append(
                datetime.fromisoformat(ts.text.replace("Z", "+00:00")).astimezone(
                    TIMEZONE
                )
            )

    placemark = tree.find(".//{*}Placemark")
    if placemark is None:
        raise ValueError("MOSMIX enthält keine Station")

    forecasts = {}
    for forecast in placemark.findall(".//{*}Forecast"):
        element_name = None
        for attr_name, attr_value in forecast.attrib.items():
            if (
                attr_name.endswith("elementName")
                or local_name(attr_name) == "elementName"
            ):
                element_name = attr_value
                break
        value = find_value_text(forecast)
        if element_name:
            forecasts[element_name] = value.split()

    def get_series(name: str) -> list[float | None]:
        series = forecasts.get(name, [])
        values: list[float | None] = []
        for entry in series:
            if entry in ("-", "", "-999", "-999.0"):
                values.append(None)
            else:
                values.append(float(entry))
        return values

    def get_series_first(names: tuple[str, ...]) -> list[float | None]:
        for name in names:
            series = get_series(name)
            if series:
                return series
        return []

    temps_k = get_series("TTT")
    precip_prob = get_series_first(("wwP", "wwP6"))
    precip_amount = get_series("RR1c")
    wind_speed = get_series("FF")
    wind_dir = get_series("DD")
    weather_code = get_series("ww")
    sunshine_daily = get_series("SunD1")

    hourly = []
    today = datetime.now(TIMEZONE).date()
    tomorrow = today + timedelta(days=1)

    for idx, ts in enumerate(timesteps):
        if ts.date() not in (today, tomorrow):
            continue
        temp_c = temps_k[idx] - 273.15 if idx < len(temps_k) and temps_k[idx] else None
        hourly.append(
            {
                "time": ts.isoformat(),
                "temperature_c": round(temp_c, 2) if temp_c is not None else None,
                "precip_probability": precip_prob[idx] if idx < len(precip_prob) else None,
                "precip_amount": precip_amount[idx] if idx < len(precip_amount) else None,
                "wind_speed": wind_speed[idx] if idx < len(wind_speed) else None,
                "wind_direction": wind_dir[idx] if idx < len(wind_dir) else None,
                "weather_code": weather_code[idx] if idx < len(weather_code) else None,
            }
        )

    today_temps = [h["temperature_c"] for h in hourly if h["temperature_c"] is not None]
    today_summary = {
        "max_temp": max(today_temps) if today_temps else None,
        "min_temp": min(today_temps) if today_temps else None,
        "sunshine_hours": None,
        "weather_symbol": None,
    }
    if sunshine_daily:
        sun_today = sunshine_daily[0]
        if sun_today is not None:
            today_summary["sunshine_hours"] = round(sun_today / 60.0, 1)

    today_summary["weather_symbol"] = _weather_symbol_from_code(
        hourly[0]["weather_code"] if hourly else None
    )

    return hourly, today_summary


def _parse_warning_xml(xml_bytes: bytes) -> list[dict]:
    tree = ET.fromstring(xml_bytes)
    warnings: list[dict] = []

    def local_name(tag: str) -> str:
        return tag.split("}", 1)[-1] if "}" in tag else tag

    for alert in tree.findall(".//{*}alert"):
        for info in alert.findall(".//{*}info"):
            for area in info.findall(".//{*}area"):
                desc = ""
                for child in area:
                    if local_name(child.tag) == "areaDesc":
                        desc = (child.text or "").strip()
                        break
                if not desc:
                    continue
                if DWD_WARNING_AREA.lower() not in desc.lower():
                    continue
                warnings.append(
                    {
                        "area": desc,
                        "severity": info.findtext(".//{*}severity", default=""),
                        "onset": info.findtext(".//{*}onset", default=""),
                        "expires": info.findtext(".//{*}expires", default=""),
                        "headline": info.findtext(".//{*}headline", default=""),
                        "description": info.findtext(".//{*}description", default=""),
                    }
                )
    return warnings


def _fetch_latest_warning_xml() -> bytes:
    listing = _download_text(WARNINGS_BASE_URL)
    matches = re.findall(
        r'href="(Z_CAP_C_EDZW_\\d{14}_PVW_STATUS_PREMIUMD\\.xml)"', listing
    )
    if not matches:
        raise ValueError("Keine Warnungsdateien gefunden")
    latest_name = max(matches)
    return _download(f"{WARNINGS_BASE_URL}{latest_name}")


def _weather_symbol_from_code(code: float | None) -> str:
    if code is None:
        return "❔"
    code_int = int(code)
    if code_int in (0, 1, 2):
        return "☀️"
    if code_int in (3, 4):
        return "⛅"
    if code_int in (45, 48):
        return "🌫️"
    if 51 <= code_int <= 67:
        return "🌦️"
    if 71 <= code_int <= 77:
        return "❄️"
    if 80 <= code_int <= 82:
        return "🌧️"
    if 95 <= code_int <= 99:
        return "⛈️"
    return "☁️"


def fetch_weather() -> WeatherData:
    """Lädt Wetterdaten (MOSMIX + Warnungen) mit Cache."""
    if WEATHER_CACHE.is_valid() and WEATHER_CACHE.get() is not None:
        return WEATHER_CACHE.get()  # type: ignore[return-value]

    warnings: list[dict] = []
    hourly: list[dict] = []
    today_summary: dict = {
        "max_temp": None,
        "min_temp": None,
        "sunshine_hours": None,
        "weather_symbol": None,
    }

    try:
        kmz_bytes = _download(MOSMIX_URL.format(station=DWD_STATION_ID))
        kml_bytes = _extract_kml_from_kmz(kmz_bytes)
        hourly, today_summary = _parse_mosmix(kml_bytes)
    except Exception:
        LOGGER.exception("Fehler beim Laden der MOSMIX Daten")

    try:
        warnings_xml = _fetch_latest_warning_xml()
        warnings = _parse_warning_xml(warnings_xml)
    except Exception:
        LOGGER.exception("Fehler beim Laden der Wetterwarnungen")

    data = WeatherData(
        updated_at=datetime.now(TIMEZONE),
        hourly=hourly,
        today_summary=today_summary,
        warnings=warnings,
    )
    WEATHER_CACHE.set(data)
    return data
