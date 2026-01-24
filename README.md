# Hausserver (Raspberry Pi)

Ein vollständig lauffähiges Raspberry-Pi-Projekt zum Messen von Umweltdaten (DHT22), zur Lüftersteuerung (GPIO), zum Speichern in SQLite sowie zum Anzeigen der Daten über eine deutsche Weboberfläche mit Chart.js.

**Zeitzone:** Alle Zeitstempel werden in lokaler Zeit gespeichert und angezeigt. Verbindliche Zeitzone: **Europe/Berlin**. Diese Entscheidung ist in `config.py` und im Code dokumentiert.

## Projektstruktur

```
hausserver/
├── app.py
├── config.py
├── db.py
├── fan.py
├── sensors.py
├── tasks.py
├── weather.py
├── requirements.txt
├── README.md
├── static/
│   ├── css/styles.css
│   ├── js/dach.js
│   ├── js/wetter.js
│   └── img/
│       ├── dach.svg
│       └── wetter.svg
├── templates/
│   ├── base.html
│   ├── dach.html
│   ├── index.html
│   └── wetter.html
└── systemd/
    └── hausserver.service
```

## Installation (Raspberry Pi OS)

### 1) Systempakete

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip sqlite3 git
```

### 2) Projekt holen und virtuelles Environment

```bash
git clone <REPO_URL> hausserver
cd hausserver
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3) GPIO und Sensoren

- **DHT22** an **GPIO 23** (BCM) anschließen.
- **Lüfter** an **GPIO 4** (BCM) anschließen (über Transistor/Relais je nach Lüfter!).
- Stromversorgung sicherstellen und die Schaltung gemäß DHT22/Relais-Datenblatt aufbauen.

### 4) Verzeichnisse und Rechte

```bash
sudo mkdir -p /var/lib/hausserver
sudo mkdir -p /var/log/hausserver
sudo chown -R pi:pi /var/lib/hausserver /var/log/hausserver
```

### 5) Starten

```bash
python app.py
```

Anschließend im Browser öffnen: `http://<raspberrypi>:5000`

## Systemd Autostart

Service-Datei liegt unter `systemd/hausserver.service`. Kopieren und aktivieren:

```bash
sudo cp systemd/hausserver.service /etc/systemd/system/hausserver.service
sudo systemctl daemon-reload
sudo systemctl enable hausserver.service
sudo systemctl start hausserver.service
```

Logs prüfen:

```bash
journalctl -u hausserver.service -f
```

## Datenbank

Die Datenbank wird automatisch initialisiert (`db.py`). Schema:

```sql
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    temperature_c REAL NOT NULL,
    humidity_percent REAL NOT NULL,
    dew_point_c REAL NOT NULL
);
```

Ältere Daten (> 6 Monate) werden automatisch entfernt.

## Konfiguration

Alle zentralen Parameter sind in `config.py` zusammengefasst (GPIO-Pins, Intervalle, Schwellenwerte, DB-Pfad, Cache-Zeit, Zeitzone).

## Hinweise zur Wetterdatenquelle (DWD OpenData)

- Wetterdaten stammen aus DWD OpenData (MOSMIX + CAP Warnungen).
- Standardmäßig ist `DWD_STATION_ID = 10433` (Rheinstetten). Falls eine andere Station benötigt wird, kann sie in `config.py` angepasst werden.
- Wetterwarnungen werden nach `DWD_WARNING_AREA` gefiltert (Standard: Rheinstetten).

## Wartung

- Logfile: `/var/log/hausserver/hausserver.log`
- Datenbank: `/var/lib/hausserver/hausserver.db`

## Lizenz

MIT
