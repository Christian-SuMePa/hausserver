"""Flask Anwendung für den Hausserver."""
from __future__ import annotations

import atexit
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from logging.handlers import RotatingFileHandler

from config import LOG_BACKUP_COUNT, LOG_MAX_BYTES, LOG_PATH, SMOOTHING_WINDOW, TIMEZONE
from db import fetch_latest_measurement, fetch_measurements_for_day, init_db
from fan import FanController
from sensors import read_cpu_temperature_c
from tasks import measurement_loop
from weather import fetch_weather


def setup_logging() -> None:
    """Konfiguriert rotierendes Dateilogging."""
    log_path = Path(LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        LOG_PATH, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


def smooth_series(values: list[float | None], window: int) -> list[float | None]:
    """Berechnet den gleitenden Mittelwert für eine Liste von Messwerten."""
    smoothed: list[float | None] = []
    for idx in range(len(values)):
        start = max(0, idx - window + 1)
        window_vals = [v for v in values[start : idx + 1] if v is not None]
        if not window_vals:
            smoothed.append(None)
        else:
            smoothed.append(round(sum(window_vals) / len(window_vals), 2))
    return smoothed


def create_app() -> Flask:
    setup_logging()
    init_db()

    app = Flask(__name__)

    @app.route("/")
    def index():
        cpu_temp = read_cpu_temperature_c()
        return render_template("index.html", cpu_temp=cpu_temp)

    @app.route("/dach")
    def dach():
        latest = fetch_latest_measurement()
        return render_template("dach.html", latest=latest)

    @app.route("/wetter")
    def wetter():
        weather = fetch_weather()
        return render_template("wetter.html", weather=weather)

    @app.route("/api/dach")
    def api_dach():
        date_str = request.args.get("date")
        if not date_str:
            return jsonify({"error": "Datum fehlt"}), 400
        try:
            day = datetime.fromisoformat(date_str).date()
        except ValueError:
            return jsonify({"error": "Ungültiges Datum"}), 400

        day_start = datetime.combine(day, datetime.min.time(), tzinfo=TIMEZONE)
        day_end = datetime.combine(day, datetime.max.time(), tzinfo=TIMEZONE)

        rows = fetch_measurements_for_day(day_start, day_end)
        times = [row["ts"] for row in rows]
        temps = [row["temperature_c"] for row in rows]
        humidity = [row["humidity_percent"] for row in rows]
        dew = [row["dew_point_c"] for row in rows]

        response = {
            "times": times,
            "raw": {
                "temperature": temps,
                "humidity": humidity,
                "dew_point": dew,
            },
            "smoothed": {
                "temperature": smooth_series(temps, SMOOTHING_WINDOW),
                "humidity": smooth_series(humidity, SMOOTHING_WINDOW),
                "dew_point": smooth_series(dew, SMOOTHING_WINDOW),
            },
        }
        return jsonify(response)

    @app.route("/api/wetter")
    def api_wetter():
        weather = fetch_weather()
        return jsonify(
            {
                "updated_at": weather.updated_at.isoformat(),
                "hourly": weather.hourly,
                "today_summary": weather.today_summary,
                "warnings": weather.warnings,
            }
        )

    return app


def start_background_tasks() -> threading.Event:
    """Startet Hintergrundthreads für Messung und Lüfter."""
    stop_event = threading.Event()

    fan = FanController()

    measurement_thread = threading.Thread(
        target=measurement_loop, args=(stop_event,), daemon=True
    )
    fan_thread = threading.Thread(target=fan.run_loop, args=(stop_event,), daemon=True)

    measurement_thread.start()
    fan_thread.start()

    def cleanup():
        stop_event.set()
        fan.cleanup()

    atexit.register(cleanup)

    return stop_event


app = create_app()

if __name__ == "__main__":
    # verhindern, dass Flask reloader doppelte Threads startet
    if not app.debug or threading.current_thread().name == "MainThread":
        start_background_tasks()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
