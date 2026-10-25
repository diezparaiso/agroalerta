import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.schemas import AgronomicActivity, AgronomicActivityCreate, CropCampaign, CropCampaignCreate, Device, DeviceCreate, FieldReportCreate, Parcel, ParcelCreate, RiskSnapshot, TelemetryCreate
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
                CREATE TABLE IF NOT EXISTS agronomic_activities (
                    id TEXT PRIMARY KEY,
                    parcel_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    detail TEXT,
                    occurred_at TEXT NOT NULL,
                    quantity REAL,
                    unit TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS crop_campaigns (
                    id TEXT PRIMARY KEY,
                    parcel_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    crop_type TEXT NOT NULL,
                    season_label TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL,
                    variety TEXT,
                    target_yield_t_ha REAL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS campaign_decisions (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    disease_code TEXT NOT NULL,
                    decision_score REAL NOT NULL,
                    priority TEXT NOT NULL,
                    headline TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS campaign_results (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    harvested_at TEXT NOT NULL,
                    harvested_quantity_kg REAL NOT NULL,
                    productive_area_ha REAL NOT NULL,
                    marketable_quantity_kg REAL,
                    quality_grade TEXT,
                    destination TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    yield_kg_ha REAL NOT NULL DEFAULT 0,
                    target_yield_kg_ha REAL,
                    target_deviation_pct REAL
                );
                CREATE TABLE IF NOT EXISTS push_tokens (
                    token TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS irrigation_events (
                    id TEXT PRIMARY KEY,
                    parcel_id TEXT NOT NULL,
                    campaign_id TEXT,
                    owner_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    water_liters REAL,
                    method TEXT NOT NULL,
                    notes TEXT
                );
                '''
            )
            for table in ('field_reports', 'telemetry', 'devices'):
                columns = {row['name'] for row in connection.execute(f'PRAGMA table_info({table})')}
                if 'owner_id' not in columns:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'anonymous'")
            # Migración de resultados de campaña: el modelo CampaignResult exige
            # yield_kg_ha y las bases existentes se crearon sin estas columnas.
            result_columns = {row['name'] for row in connection.execute('PRAGMA table_info(campaign_results)')}
            if 'yield_kg_ha' not in result_columns:
                connection.execute('ALTER TABLE campaign_results ADD COLUMN yield_kg_ha REAL NOT NULL DEFAULT 0')
            if 'target_yield_kg_ha' not in result_columns:
                connection.execute('ALTER TABLE campaign_results ADD COLUMN target_yield_kg_ha REAL')
            if 'target_deviation_pct' not in result_columns:
                connection.execute('ALTER TABLE campaign_results ADD COLUMN target_deviation_pct REAL')

    def create_irrigation_event(self, event: dict[str, object]) -> dict[str, object]:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO irrigation_events
                (id, parcel_id, campaign_id, owner_id, started_at, duration_minutes, water_liters, method, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event['id'], event['parcel_id'], event['campaign_id'], event['owner_id'],
                 event['started_at'], event['duration_minutes'], event['water_liters'],
                 event['method'], event['notes']),
            )
        return event

    def list_irrigation_events(self, parcel_id: str, owner_id: str, limit: int = 100) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM irrigation_events WHERE parcel_id = ? AND owner_id = ? ORDER BY started_at DESC LIMIT ?",
                (parcel_id, owner_id, max(1, min(limit, 200))),
            ).fetchall()
        return [dict(row) for row in rows]

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

    def create_activity(self, activity_id: str, payload: AgronomicActivityCreate) -> AgronomicActivity:
        created_at = datetime.now(timezone.utc)
        owner_id = payload.owner_id or 'anonymous'
        with self._connect() as connection:
            connection.execute(
                'INSERT INTO agronomic_activities (id, parcel_id, owner_id, activity_type, title, detail, occurred_at, quantity, unit, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (activity_id, payload.parcel_id, owner_id, payload.activity_type, payload.title, payload.detail, payload.occurred_at.isoformat(), payload.quantity, payload.unit, created_at.isoformat()),
            )
        return AgronomicActivity(id=activity_id, created_at=created_at, **payload.model_dump())

    def list_activities(self, parcel_id: str, owner_id: str, limit: int = 100) -> list[AgronomicActivity]:
        with self._connect() as connection:
            rows = connection.execute(
                'SELECT id, parcel_id, owner_id, activity_type, title, detail, occurred_at, quantity, unit, created_at FROM agronomic_activities WHERE parcel_id = ? AND owner_id = ? ORDER BY occurred_at DESC LIMIT ?',
                (parcel_id, owner_id, limit),
            ).fetchall()
        return [AgronomicActivity(**dict(row)) for row in rows]


    def create_campaign(self, campaign_id: str, payload: CropCampaignCreate) -> CropCampaign:
        now = datetime.now(timezone.utc)
        owner_id = payload.owner_id or 'anonymous'
        with self._connect() as connection:
            connection.execute(
                'INSERT INTO crop_campaigns (id, parcel_id, owner_id, crop_type, season_label, started_at, ended_at, status, variety, target_yield_t_ha, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (campaign_id, payload.parcel_id, owner_id, payload.crop_type, payload.season_label, payload.started_at.isoformat(), payload.ended_at.isoformat() if payload.ended_at else None, payload.status, payload.variety, payload.target_yield_t_ha, payload.notes, now.isoformat(), now.isoformat()),
            )
        return CropCampaign(id=campaign_id, created_at=now, updated_at=now, **payload.model_dump())

    def list_campaigns(self, parcel_id: str, owner_id: str) -> list[CropCampaign]:
        with self._connect() as connection:
            rows = connection.execute(
                'SELECT * FROM crop_campaigns WHERE parcel_id = ? AND owner_id = ? ORDER BY started_at DESC',
                (parcel_id, owner_id),
            ).fetchall()
        return [CropCampaign(**dict(row)) for row in rows]

    def get_campaign(self, campaign_id: str, owner_id: str) -> CropCampaign | None:
        with self._connect() as connection:
            row = connection.execute(
                'SELECT * FROM crop_campaigns WHERE id = ? AND owner_id = ?',
                (campaign_id, owner_id),
            ).fetchone()
        return CropCampaign(**dict(row)) if row else None

    def update_campaign_status(self, campaign_id: str, owner_id: str, status: str, ended_at: datetime | None = None) -> CropCampaign | None:
        now = datetime.now(timezone.utc)
        with self._connect() as connection:
            result = connection.execute(
                'UPDATE crop_campaigns SET status = ?, ended_at = ?, updated_at = ? WHERE id = ? AND owner_id = ?',
                (status, ended_at.isoformat() if ended_at else None, now.isoformat(), campaign_id, owner_id),
            )
        return self.get_campaign(campaign_id, owner_id) if result.rowcount else None


    def create_campaign_decision(self, decision_id: str, campaign_id: str, owner_id: str, decision: dict) -> None:
        with self._connect() as connection:
            connection.execute(
                'INSERT INTO campaign_decisions (id, campaign_id, owner_id, disease_code, decision_score, priority, headline, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (decision_id, campaign_id, owner_id, decision['disease_code'], decision['decision_score'], decision['priority'], decision['headline'], decision['calculated_at']),
            )

    def list_campaign_decisions(self, campaign_id: str, owner_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                'SELECT id, campaign_id, owner_id, disease_code, decision_score, priority, headline, created_at FROM campaign_decisions WHERE campaign_id = ? AND owner_id = ? ORDER BY created_at DESC',
                (campaign_id, owner_id),
            ).fetchall()
        return [dict(row) for row in rows]


    def create_campaign_result(self, result_id: str, campaign_id: str, owner_id: str, payload: dict) -> dict:
        with self._connect() as connection:
            connection.execute(
                'INSERT INTO campaign_results (id, campaign_id, owner_id, harvested_at, harvested_quantity_kg, productive_area_ha, marketable_quantity_kg, quality_grade, destination, notes, created_at, yield_kg_ha, target_yield_kg_ha, target_deviation_pct) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (result_id, campaign_id, owner_id, payload['harvested_at'].isoformat(), payload['harvested_quantity_kg'], payload['productive_area_ha'], payload.get('marketable_quantity_kg'), payload.get('quality_grade'), payload.get('destination'), payload.get('notes'), payload['created_at'].isoformat(), payload.get('yield_kg_ha'), payload.get('target_yield_kg_ha'), payload.get('target_deviation_pct')),
            )
        return {'id': result_id, 'owner_id': owner_id, **payload}

    def list_campaign_results(self, campaign_id: str, owner_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                'SELECT * FROM campaign_results WHERE campaign_id = ? AND owner_id = ? ORDER BY harvested_at DESC',
                (campaign_id, owner_id),
            ).fetchall()
        return [dict(row) for row in rows]

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

    def list_risk_snapshots_since(self, parcel_id: str, owner_id: str, since: datetime, limit: int = 20) -> list[RiskSnapshot]:
        with self._connect() as connection:
            rows = connection.execute(
                'SELECT parcel_id, owner_id, disease_code, risk_score, risk_level, calculated_at FROM risk_snapshots WHERE parcel_id = ? AND owner_id = ? AND calculated_at >= ? ORDER BY calculated_at DESC LIMIT ?',
                (parcel_id, owner_id, since.isoformat(), limit),
            ).fetchall()
        return [RiskSnapshot(**dict(row)) for row in rows]

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
