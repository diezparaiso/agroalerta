import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.schemas import Device, DeviceCreate, FieldReportCreate, Parcel, ParcelCreate, RiskSnapshot, TelemetryCreate
from app.schemas_push import PushTokenCreate


class Storage:
    def __init__(self) -> None:
        database_url = os.getenv('AGROALERTA_DB_PATH', 'backend/agroalerta.db')
        self.path = Path(database_url)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def health(self) -> bool:
        with self._connect() as connection:
            connection.execute('SELECT 1').fetchone()
        return True

    def _initialize(self) -> None:
        with self._connect() as connection:
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
                    measured_at TEXT NOT NULL
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

    def update_parcel(self, parcel_id: str, payload: ParcelCreate, owner_id: str | None = None) -> Parcel | None:
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            query = '''UPDATE parcels SET label = ?, latitude = ?, longitude = ?,
                   crop_type = ?, comarca = ?, updated_at = ? WHERE id = ?'''
            parameters: tuple[object, ...] = (
                    payload.label,
                    payload.latitude,
                    payload.longitude,
                    payload.crop_type,
                    payload.comarca,
                    now.isoformat(),
                    parcel_id,
                )
            if owner_id is not None:
                query += ' AND owner_id = ?'
                parameters += (owner_id,)
            result = connection.execute(query, parameters)
        return self.get_parcel(parcel_id, owner_id) if result.rowcount else None

    def create_report(self, report_id: str, payload: FieldReportCreate) -> None:
        with self._connect() as connection:
            connection.execute(
                'INSERT INTO field_reports (id, parcel_id, owner_id, payload, created_at) VALUES (?, ?, ?, ?, ?)',
                (report_id, payload.parcel_id, payload.owner_id or 'anonymous', json.dumps(payload.model_dump(), default=str), datetime.now(timezone.utc).isoformat()),
            )

    def create_telemetry(self, payload: TelemetryCreate) -> None:
        with self._connect() as connection:
            connection.execute(
                'INSERT INTO telemetry (parcel_id, owner_id, device_id, payload, measured_at) VALUES (?, ?, ?, ?, ?)',
                (payload.parcel_id, payload.owner_id or 'anonymous', payload.device_id, json.dumps(payload.model_dump(), default=str), payload.measured_at.isoformat()),
            )

    def latest_telemetry(self, parcel_id: str, owner_id: str | None = None) -> TelemetryCreate | None:
        with self._connect() as connection:
            query = 'SELECT payload FROM telemetry WHERE parcel_id = ?'
            parameters: tuple[str, ...] = (parcel_id,)
            if owner_id is not None:
                query += ' AND owner_id = ?'
                parameters += (owner_id,)
            row = connection.execute(query + ' ORDER BY measured_at DESC LIMIT 1', parameters).fetchone()
        return TelemetryCreate(**json.loads(row['payload'])) if row else None

    def create_device(self, device: Device) -> Device:
        with self._connect() as connection:
            connection.execute('INSERT OR REPLACE INTO devices (device_id, parcel_id, name, device_type, registered_at, active, owner_id) VALUES (?, ?, ?, ?, ?, ?, ?)', (device.device_id, device.parcel_id, device.name, device.device_type, device.registered_at.isoformat(), int(device.active), device.owner_id or 'anonymous'))
        return device

    def list_devices(self, parcel_id: str, owner_id: str | None = None) -> list[Device]:
        with self._connect() as connection:
            query = 'SELECT * FROM devices WHERE parcel_id = ?'
            parameters: tuple[str, ...] = (parcel_id,)
            if owner_id is not None:
                query += ' AND owner_id = ?'
                parameters += (owner_id,)
            rows = connection.execute(query + ' ORDER BY name', parameters).fetchall()
        return [Device(device_id=row['device_id'], parcel_id=row['parcel_id'], name=row['name'], device_type=row['device_type'], registered_at=row['registered_at'], active=bool(row['active']), owner_id=row['owner_id']) for row in rows]

    def save_risk_snapshot(self, snapshot: RiskSnapshot) -> None:
        with self._connect() as connection:
            previous = connection.execute('SELECT risk_score, risk_level, calculated_at FROM risk_snapshots WHERE parcel_id = ? AND owner_id = ? AND disease_code = ? ORDER BY calculated_at DESC LIMIT 1', (snapshot.parcel_id, snapshot.owner_id or 'anonymous', snapshot.disease_code)).fetchone()
            if previous and previous['risk_score'] == snapshot.risk_score and previous['risk_level'] == snapshot.risk_level:
                previous_time = datetime.fromisoformat(previous['calculated_at'])
                if snapshot.calculated_at - previous_time < timedelta(hours=1):
                    return
            connection.execute('INSERT INTO risk_snapshots (parcel_id, owner_id, disease_code, risk_score, risk_level, calculated_at) VALUES (?, ?, ?, ?, ?, ?)', (snapshot.parcel_id, snapshot.owner_id or 'anonymous', snapshot.disease_code, snapshot.risk_score, snapshot.risk_level, snapshot.calculated_at.isoformat()))

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
