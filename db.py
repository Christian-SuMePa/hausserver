"""SQLite Datenbankzugriff für Messungen."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Iterable

from config import DATA_RETENTION_MONTHS, DB_PATH, DB_TIMEOUT_SECONDS, TIMEZONE


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    temperature_c REAL NOT NULL,
    humidity_percent REAL NOT NULL,
    dew_point_c REAL NOT NULL
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_measurements_ts ON measurements (ts);
"""


def get_connection() -> sqlite3.Connection:
    """Öffnet eine neue Datenbankverbindung mit WAL und Zeitlimit."""
    conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    """Initialisiert das Datenbankschema."""
    with get_connection() as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.execute(CREATE_INDEX_SQL)


def insert_measurement(
    timestamp: datetime, temperature_c: float, humidity_percent: float, dew_point_c: float
) -> None:
    """Speichert eine Messung, anschließend werden alte Daten bereinigt."""
    ts_local = timestamp.astimezone(TIMEZONE).isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO measurements (ts, temperature_c, humidity_percent, dew_point_c)
            VALUES (?, ?, ?, ?)
            """,
            (ts_local, temperature_c, humidity_percent, dew_point_c),
        )
        prune_old(conn)


def prune_old(conn: sqlite3.Connection | None = None) -> None:
    """Entfernt Messungen, die älter als DATA_RETENTION_MONTHS sind."""
    own_conn = conn is None
    if own_conn:
        conn = get_connection()
    assert conn is not None

    cutoff = datetime.now(TIMEZONE)
    cutoff_month = cutoff.month - DATA_RETENTION_MONTHS
    year = cutoff.year
    while cutoff_month <= 0:
        cutoff_month += 12
        year -= 1
    cutoff = cutoff.replace(year=year, month=cutoff_month)
    cutoff_iso = cutoff.isoformat()

    conn.execute("DELETE FROM measurements WHERE ts < ?", (cutoff_iso,))
    if own_conn:
        conn.commit()
        conn.close()


def fetch_latest_measurement() -> sqlite3.Row | None:
    """Liest die neueste Messung."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM measurements ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    return row


def fetch_measurements_for_day(day_start: datetime, day_end: datetime) -> Iterable[sqlite3.Row]:
    """Liest Messungen für einen Zeitraum (lokale Zeit)."""
    start_iso = day_start.astimezone(TIMEZONE).isoformat()
    end_iso = day_end.astimezone(TIMEZONE).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM measurements
            WHERE ts >= ? AND ts <= ?
            ORDER BY ts ASC
            """,
            (start_iso, end_iso),
        ).fetchall()
    return rows
