import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.schemas import Alert, Device, DeviceCreate, FieldReportCreate, Parcel, ParcelCreate, RiskSnapshot, TelemetryCreate
from app.schemas_push import PushTokenCreate


class Storage:
    def __init__(self) -> None:
        database_url = os.getenv('AGROALERTA_DB_URL', os.getenv('AGROALERTA_DB_PATH', 'backend/agroalerta.db'))
        if database_url.startswith('sqlite:///'):
            database_url = database_url.removeprefix('sqlite:///')
        elif '://' in database_url:
            raise ValueError('AGROALERTA_DB_URL currently supports SQLite only; configure PostgreSQL adapter before using another driver')
        self.path = Path(database_url)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.execute('PRAGMA busy_timeout = 30000')
        connection.execute('PRAGMA journal_mode = WAL')
        connection.execute('PRAGMA foreign_keys = ON')
        connection.row_factory = sqlite3.Row
        return connection

    def health(self) -> bool:
        with self._connect() as connection:
            connection.execute('SELECT 1').fetchone()
        return True

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                '''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                '''
            )
            connection.executescript(
                '''
                CREATE TABLE IF NOT EXISTS parcels (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    crop_type TEXT NOT NULL,
                    comarca TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS field_reports (
                    id TEXT PRIMARY KEY,
                    parcel_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parcel_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    measured_at TEXT NOT NULL,
                    telemetry_id TEXT UNIQUE
                );
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    parcel_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    registered_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS risk_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parcel_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    disease_code TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    calculated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    parcel_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    disease_code TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    valid_until TEXT,
                    notified_at TEXT,
                    dedup_key TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS source_records (
                    source_code TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    observed_at TEXT,
                    province TEXT,
                    municipality TEXT,
                    parcel_reference TEXT,
                    latitude REAL,
                    longitude REAL,
                    payload TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    PRIMARY KEY (source_code, external_id)
                );
                CREATE TABLE IF NOT EXISTS push_tokens (
                    token TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                '''
            )
            for table in ('field_reports', 'telemetry', 'devices'):
                columns = {row['name'] for row in connection.execute(f'PRAGMA table_info({table})')}
                if 'owner_id' not in columns:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'anonymous'")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS weather_stations (
                    source_code TEXT NOT NULL,
                    station_code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    province TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    altitude_m REAL,
                    active INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (source_code, station_code)
                );
                CREATE TABLE IF NOT EXISTS weather_observations (
                    source_code TEXT NOT NULL,
                    station_code TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    temperature_c REAL,
                    relative_humidity REAL,
                    rainfall_mm_24h REAL,
                    confidence TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    PRIMARY KEY (source_code, station_code, observed_at)
                )
                """
            )
            source_columns = {row['name'] for row in connection.execute('PRAGMA table_info(source_records)')}
            if 'latitude' not in source_columns:
                connection.execute('ALTER TABLE source_records ADD COLUMN latitude REAL')
            if 'longitude' not in source_columns:
                connection.execute('ALTER TABLE source_records ADD COLUMN longitude REAL')
            columns = {row['name'] for row in connection.execute('PRAGMA table_info(telemetry)')}
            if 'telemetry_id' not in columns:
                connection.execute('ALTER TABLE telemetry ADD COLUMN telemetry_id TEXT')
            connection.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_telemetry_telemetry_id ON telemetry(telemetry_id) WHERE telemetry_id IS NOT NULL')
            self._record_schema_version(connection, 2)

    @staticmethod
    def _record_schema_version(connection: sqlite3.Connection, version: int) -> None:
        connection.execute(
            'INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)',
            (version, datetime.now(timezone.utc).isoformat()),
        )

    def schema_version(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                'SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations'
            ).fetchone()
        return int(row['version'])

    def list_parcels(self, owner_id: str | None = None) -> list[Parcel]:
        with self._connect() as connection:
            if owner_id is None:
                rows = connection.execute('SELECT * FROM parcels ORDER BY label').fetchall()
            else:
                rows = connection.execute('SELECT * FROM parcels WHERE owner_id = ? ORDER BY label', (owner_id,)).fetchall()
        return [Parcel(**dict(row)) for row in rows]

    def get_parcel(self, parcel_id: str, owner_id: str | None = None) -> Parcel | None:
        with self._connect() as connection:
            query = 'SELECT * FROM parcels WHERE id = ?'
            parameters: tuple[str, ...] = (parcel_id,)
            if owner_id is not None:
                query += ' AND owner_id = ?'
                parameters += (owner_id,)
            row = connection.execute(query, parameters).fetchone()
        return Parcel(**dict(row)) if row else None

    def create_parcel(self, parcel: Parcel) -> Parcel:
        with self._connect() as connection:
            connection.execute(
                'INSERT INTO parcels VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    parcel.id,
                    parcel.owner_id,
                    parcel.label,
                    parcel.latitude,
                    parcel.longitude,
                    parcel.crop_type,
                    parcel.comarca,
                    parcel.created_at.isoformat(),
                    parcel.updated_at.isoformat(),
                ),
            )
        return parcel

    def delete_parcel(self, parcel_id: str, owner_id: str | None = None) -> bool:
        with self._connect() as connection:
            query = 'DELETE FROM parcels WHERE id = ?'
            parameters: tuple[str, ...] = (parcel_id,)
            if owner_id is not None:
                query += ' AND owner_id = ?'
                parameters += (owner_id,)
            result = connection.execute(query, parameters)
        return result.rowcount > 0

    def update_parcel(
        self,
        parcel_id: str,
        payload: ParcelCreate,
        owner_id: str | None = None,
        expected_updated_at: datetime | None = None,
    ) -> Parcel | None:
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            query = '''UPDATE parcels SET label = ?, latitude = ?, longitude = ?,
                   crop_type = ?, comarca = ?, updated_at = ? WHERE id = ?'''
            parameters: list[object] = [
                payload.label,
                payload.latitude,
                payload.longitude,
                payload.crop_type,
                payload.comarca,
                now.isoformat(),
                parcel_id,
            ]
            if owner_id is not None:
                query += ' AND owner_id = ?'
                parameters.append(owner_id)
            if expected_updated_at is not None:
                query += ' AND updated_at = ?'
                parameters.append(expected_updated_at.isoformat())
            result = connection.execute(query, tuple(parameters))
        return self.get_parcel(parcel_id, owner_id) if result.rowcount else None

    def create_report(self, report_id: str, payload: FieldReportCreate) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                'INSERT OR IGNORE INTO field_reports (id, parcel_id, owner_id, payload, created_at) VALUES (?, ?, ?, ?, ?)',
                (report_id, payload.parcel_id, payload.owner_id or 'anonymous', json.dumps(payload.model_dump(), default=str), datetime.now(timezone.utc).isoformat()),
            )
        return cursor.rowcount > 0

    def create_telemetry(self, payload: TelemetryCreate) -> bool:
        with self._connect() as connection:
            result = connection.execute(
                'INSERT OR IGNORE INTO telemetry (parcel_id, owner_id, device_id, payload, measured_at, telemetry_id) VALUES (?, ?, ?, ?, ?, ?)',
                (payload.parcel_id, payload.owner_id or 'anonymous', payload.device_id, json.dumps(payload.model_dump(), default=str), payload.measured_at.isoformat(), payload.telemetry_id),
            )
        return result.rowcount > 0

    def latest_telemetry(self, parcel_id: str, owner_id: str | None = None) -> TelemetryCreate | None:
        with self._connect() as connection:
            query = 'SELECT payload FROM telemetry WHERE parcel_id = ?'
            parameters: tuple[str, ...] = (parcel_id,)
            if owner_id is not None:
                query += ' AND owner_id = ?'
                parameters += (owner_id,)
            row = connection.execute(query + ' ORDER BY measured_at DESC LIMIT 1', parameters).fetchone()
        return TelemetryCreate(**json.loads(row['payload'])) if row else None

    def list_latest_telemetry(self, parcel_id: str, owner_id: str | None = None, limit: int = 24, since_hours: int | None = None, device_id: str | None = None) -> list[dict]:
        with self._connect() as connection:
            query = 'SELECT id, device_id, payload, measured_at FROM telemetry WHERE parcel_id = ?'
            parameters: tuple[object, ...] = (parcel_id,)
            if owner_id is not None:
                query += ' AND owner_id = ?'
                parameters += (owner_id,)
            if device_id is not None:
                query += ' AND device_id = ?'
                parameters += (device_id,)
            if since_hours is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
                query += ' AND measured_at >= ?'
                parameters += (cutoff.isoformat(),)
            query += ' ORDER BY measured_at DESC LIMIT ?'
            parameters += (max(1, min(limit, 200)),)
            rows = connection.execute(query, parameters).fetchall()
        return [
            {'id': row['id'], 'device_id': row['device_id'], **json.loads(row['payload']), 'measured_at': row['measured_at']}
            for row in rows
        ]

    def create_device(self, device: Device) -> Device:
        with self._connect() as connection:
            connection.execute('INSERT OR REPLACE INTO devices (device_id, parcel_id, name, device_type, registered_at, active, owner_id) VALUES (?, ?, ?, ?, ?, ?, ?)', (device.device_id, device.parcel_id, device.name, device.device_type, device.registered_at.isoformat(), int(device.active), device.owner_id or 'anonymous'))
        return device

    def get_device(self, device_id: str, owner_id: str) -> Device | None:
        with self._connect() as connection:
            row = connection.execute(
                'SELECT * FROM devices WHERE device_id = ? AND owner_id = ?',
                (device_id, owner_id),
            ).fetchone()
        return Device(
            device_id=row['device_id'],
            parcel_id=row['parcel_id'],
            name=row['name'],
            device_type=row['device_type'],
            registered_at=row['registered_at'],
            active=bool(row['active']),
            owner_id=row['owner_id'],
        ) if row else None

    def update_device_active(self, device_id: str, owner_id: str, active: bool) -> Device | None:
        with self._connect() as connection:
            result = connection.execute(
                'UPDATE devices SET active = ? WHERE device_id = ? AND owner_id = ?',
                (int(active), device_id, owner_id),
            )
            if result.rowcount == 0:
                return None
        with self._connect() as connection:
            row = connection.execute(
                'SELECT * FROM devices WHERE device_id = ? AND owner_id = ?',
                (device_id, owner_id),
            ).fetchone()
        return Device(
            device_id=row['device_id'],
            parcel_id=row['parcel_id'],
            name=row['name'],
            device_type=row['device_type'],
            registered_at=row['registered_at'],
            active=bool(row['active']),
            owner_id=row['owner_id'],
        ) if row else None

    def list_devices(self, parcel_id: str, owner_id: str | None = None) -> list[Device]:
        with self._connect() as connection:
            query = 'SELECT * FROM devices WHERE parcel_id = ?'
            parameters: tuple[str, ...] = (parcel_id,)
            if owner_id is not None:
                query += ' AND owner_id = ?'
                parameters += (owner_id,)
            rows = connection.execute(query + ' ORDER BY name', parameters).fetchall()
        return [Device(device_id=row['device_id'], parcel_id=row['parcel_id'], name=row['name'], device_type=row['device_type'], registered_at=row['registered_at'], active=bool(row['active']), owner_id=row['owner_id']) for row in rows]

    def list_device_health(self, parcel_id: str, owner_id: str | None = None) -> list[dict]:
        with self._connect() as connection:
            query = """
                SELECT d.device_id, d.parcel_id, d.active,
                       MAX(t.measured_at) AS last_seen_at,
                       COUNT(t.id) AS telemetry_count
                FROM devices d
                LEFT JOIN telemetry t ON t.device_id = d.device_id AND t.parcel_id = d.parcel_id
                WHERE d.parcel_id = ?
            """
            parameters: tuple[object, ...] = (parcel_id,)
            if owner_id is not None:
                query += " AND d.owner_id = ?"
                parameters += (owner_id,)
            query += " GROUP BY d.device_id, d.parcel_id, d.active ORDER BY d.device_id"
            rows = connection.execute(query, parameters).fetchall()
            result = []
            for row in rows:
                battery = connection.execute(
                    "SELECT payload FROM telemetry WHERE device_id = ? AND parcel_id = ? ORDER BY measured_at DESC LIMIT 1",
                    (row["device_id"], parcel_id),
                ).fetchone()
                battery_percent = json.loads(battery["payload"]).get("battery_percent") if battery else None
                result.append({
                    "device_id": row["device_id"],
                    "parcel_id": row["parcel_id"],
                    "active": bool(row["active"]),
                    "last_seen_at": row["last_seen_at"],
                    "battery_percent": battery_percent,
                    "telemetry_count": row["telemetry_count"],
                })
            return result

    def list_georeferenced_source_records(self, source_code: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source_code, external_id, observed_at, province,
                       municipality, parcel_reference, latitude, longitude, payload
                FROM source_records
                WHERE source_code = ? AND latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY observed_at DESC
                """,
                (source_code,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_risk_snapshot(self, snapshot: RiskSnapshot) -> None:
        with self._connect() as connection:
            previous = connection.execute('SELECT risk_score, risk_level, calculated_at FROM risk_snapshots WHERE parcel_id = ? AND owner_id = ? AND disease_code = ? ORDER BY calculated_at DESC LIMIT 1', (snapshot.parcel_id, snapshot.owner_id or 'anonymous', snapshot.disease_code)).fetchone()
            if previous and previous['risk_score'] == snapshot.risk_score and previous['risk_level'] == snapshot.risk_level:
                previous_time = datetime.fromisoformat(previous['calculated_at'])
                if snapshot.calculated_at - previous_time < timedelta(hours=1):
                    return
            connection.execute('INSERT INTO risk_snapshots (parcel_id, owner_id, disease_code, risk_score, risk_level, calculated_at) VALUES (?, ?, ?, ?, ?, ?)', (snapshot.parcel_id, snapshot.owner_id or 'anonymous', snapshot.disease_code, snapshot.risk_score, snapshot.risk_level, snapshot.calculated_at.isoformat()))

    def save_alert(
        self,
        parcel_id: str,
        owner_id: str,
        disease_code: str,
        alert_type: str,
        risk_level: str,
        risk_score: float,
        message: str,
        created_at: datetime,
        valid_until: datetime | None = None,
        notified_at: datetime | None = None,
        dedup_key: str | None = None,
    ) -> Alert | None:
        key = dedup_key or f"{parcel_id}:{disease_code}:{alert_type}:{risk_level}:{created_at.isoformat()}"
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO alerts
                (parcel_id, owner_id, disease_code, alert_type, risk_level,
                 risk_score, message, created_at, valid_until, notified_at, dedup_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    parcel_id, owner_id, disease_code, alert_type, risk_level,
                    risk_score, message, created_at.isoformat(),
                    valid_until.isoformat() if valid_until else None,
                    notified_at.isoformat() if notified_at else None,
                    key,
                ),
            )
            if cursor.rowcount == 0:
                return None
            row = connection.execute(
                "SELECT id, parcel_id, owner_id, disease_code, alert_type, risk_level, risk_score, message, created_at, valid_until, notified_at FROM alerts WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return Alert(**dict(row)) if row else None

    def mark_alert_notified(self, alert_id: int, notified_at: datetime | None = None) -> None:
        timestamp = notified_at or datetime.now(timezone.utc)
        with self._connect() as connection:
            connection.execute(
                "UPDATE alerts SET notified_at = ? WHERE id = ?",
                (timestamp.isoformat(), alert_id),
            )

    def list_alerts(
        self,
        parcel_id: str | None = None,
        owner_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        with self._connect() as connection:
            query = """
                SELECT id, parcel_id, owner_id, disease_code, alert_type,
                       risk_level, risk_score, message, created_at, valid_until, notified_at
                FROM alerts
                WHERE 1 = 1
            """
            parameters: list[object] = []
            if parcel_id is not None:
                query += " AND parcel_id = ?"
                parameters.append(parcel_id)
            if owner_id is not None:
                query += " AND owner_id = ?"
                parameters.append(owner_id)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            parameters.extend((limit, offset))
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [Alert(**dict(row)) for row in rows]

    def list_risk_snapshots(self, parcel_id: str, owner_id: str, limit: int = 100, offset: int = 0) -> list[RiskSnapshot]:
        with self._connect() as connection:
            rows = connection.execute('SELECT parcel_id, owner_id, disease_code, risk_score, risk_level, calculated_at FROM risk_snapshots WHERE parcel_id = ? AND owner_id = ? ORDER BY calculated_at DESC LIMIT ? OFFSET ?', (parcel_id, owner_id, limit, offset)).fetchall()
        return [RiskSnapshot(**dict(row)) for row in rows]

    def prune_risk_snapshots(self, retention_days: int) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        with self._connect() as connection:
            connection.execute('DELETE FROM risk_snapshots WHERE calculated_at < ?', (cutoff.isoformat(),))

    def save_push_token(self, payload: PushTokenCreate) -> None:
        with self._connect() as connection:
            connection.execute('INSERT OR REPLACE INTO push_tokens (token, owner_id, platform, updated_at) VALUES (?, ?, ?, ?)', (payload.token, payload.owner_id or 'anonymous', payload.platform, datetime.now(timezone.utc).isoformat()))

    def list_push_tokens(self, owner_id: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute('SELECT token FROM push_tokens WHERE owner_id = ?', (owner_id,)).fetchall()
        return [row['token'] for row in rows]

    def delete_push_token(self, token: str, owner_id: str) -> None:
        with self._connect() as connection:
            connection.execute('DELETE FROM push_tokens WHERE token = ? AND owner_id = ?', (token, owner_id))


    def save_source_record(
        self,
        source_code: str,
        external_id: str,
        observed_at: datetime | None,
        province: str | None,
        municipality: str | None,
        parcel_reference: str | None,
        payload: dict[str, object],
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                '''
                INSERT OR REPLACE INTO source_records
                (source_code, external_id, observed_at, province, municipality, parcel_reference, latitude, longitude, payload, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    source_code,
                    external_id,
                    observed_at.isoformat() if observed_at else None,
                    province,
                    municipality,
                    parcel_reference,
                    latitude,
                    longitude,
                    json.dumps(payload, ensure_ascii=False, default=str),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return cursor.rowcount > 0

    def count_source_records(self, source_code: str) -> int:
        with self._connect() as connection:
            row = connection.execute(
                'SELECT COUNT(*) AS count FROM source_records WHERE source_code = ?',
                (source_code,),
            ).fetchone()
        return int(row['count'])

    def save_weather_station(
        self,
        source_code: str,
        station_code: str,
        name: str,
        province: str | None,
        latitude: float,
        longitude: float,
        altitude_m: float | None,
        active: bool,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO weather_stations
                (source_code, station_code, name, province, latitude, longitude,
                 altitude_m, active, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_code, station_code, name, province, latitude, longitude,
                    altitude_m, int(active), datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_weather_stations(self, source_code: str = "ria_ifapa") -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source_code, station_code, name, province, latitude,
                       longitude, altitude_m, active
                FROM weather_stations
                WHERE source_code = ? AND active = 1
                ORDER BY name
                """,
                (source_code,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_weather_observation(
        self,
        source_code: str,
        station_code: str,
        observed_at: datetime,
        latitude: float | None,
        longitude: float | None,
        temperature_c: float | None,
        relative_humidity: float | None,
        rainfall_mm_24h: float | None,
        confidence: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO weather_observations
                (source_code, station_code, observed_at, latitude, longitude,
                 temperature_c, relative_humidity, rainfall_mm_24h, confidence, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_code, station_code, observed_at.isoformat(), latitude,
                    longitude, temperature_c, relative_humidity, rainfall_mm_24h,
                    confidence, datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_weather_stations_with_latest_observation(
        self,
        source_code: str = "ria_ifapa",
        limit: int = 500,
    ) -> list[dict[str, object]]:
        """Une el catálogo canónico de estaciones con su última observación."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT s.source_code, s.station_code, s.name, s.province,
                       s.latitude, s.longitude, s.altitude_m, s.active,
                       o.observed_at, o.temperature_c, o.relative_humidity,
                       o.rainfall_mm_24h, o.confidence
                FROM weather_stations s
                LEFT JOIN (
                    SELECT *
                    FROM (
                        SELECT *,
                               ROW_NUMBER() OVER (
                                   PARTITION BY source_code, station_code
                                   ORDER BY observed_at DESC
                               ) AS row_number
                        FROM weather_observations
                    )
                    WHERE row_number = 1
                ) o
                  ON o.source_code = s.source_code
                 AND o.station_code = s.station_code
                WHERE s.source_code = ? AND s.active = 1
                ORDER BY s.name
                LIMIT ?
                """,
                (source_code, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_latest_risk_snapshot(self, parcel_id: str, owner_id: str, disease_code: str) -> RiskSnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT parcel_id, owner_id, disease_code, risk_score, risk_level, calculated_at
                FROM risk_snapshots
                WHERE parcel_id = ? AND owner_id = ? AND disease_code = ?
                ORDER BY calculated_at DESC
                LIMIT 1
                """,
                (parcel_id, owner_id, disease_code),
            ).fetchone()
        return RiskSnapshot(**dict(row)) if row else None

    def list_weather_observations(self, limit: int = 500) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source_code, station_code, observed_at, latitude, longitude,
                       temperature_c, relative_humidity, rainfall_mm_24h, confidence
                FROM weather_observations
                ORDER BY observed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_latest_weather_observations(self, limit: int = 500) -> list[dict[str, object]]:
        """Devuelve la ultima observacion disponible por estacion meteorologica."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT source_code, station_code, observed_at, latitude, longitude,
                       temperature_c, relative_humidity, rainfall_mm_24h, confidence
                FROM (
                    SELECT *,
                           ROW_NUMBER() OVER (
                               PARTITION BY source_code, station_code
                               ORDER BY observed_at DESC
                           ) AS row_number
                    FROM weather_observations
                    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                )
                WHERE row_number = 1
                ORDER BY observed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_georeferenced_source_records(self, source_code: str, limit: int = 1000) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                '''
                SELECT source_code, external_id, observed_at, province, municipality,
                       parcel_reference, latitude, longitude, payload
                FROM source_records
                WHERE source_code = ? AND latitude IS NOT NULL AND longitude IS NOT NULL
                ORDER BY observed_at DESC
                LIMIT ?
                ''',
                (source_code, limit),
            ).fetchall()
        return [dict(row) for row in rows]
