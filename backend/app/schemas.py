from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ParcelCreate(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    latitude: float = Field(ge=27, le=44)
    longitude: float = Field(ge=-19, le=5)
    crop_type: Literal["olivar", "vinedo"]
    comarca: str = Field(min_length=1, max_length=120)


class Parcel(ParcelCreate):
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime


class FieldReportCreate(BaseModel):
    report_id: str | None = None
    parcel_id: str
    type: Literal["trampa", "sintoma"]
    notes: str | None = None
    count: int | None = Field(default=None, ge=0)
    latitude: float = Field(ge=27, le=44)
    longitude: float = Field(ge=-19, le=5)
    reported_at: datetime
    photo_url: str | None = None
    owner_id: str | None = None


class RiskVariable(BaseModel):
    name: str
    value: float
    date: datetime


class DiseaseRisk(BaseModel):
    parcel_id: str
    disease_code: Literal["repilo", "mildiu"]
    risk_score: float = Field(ge=0, le=1)
    risk_level: Literal["bajo", "medio", "alto"]
    confidence_level: Literal["alta", "estimada"]
    recommendation_text: str
    variables_used: list[RiskVariable]
    calculated_at: datetime
    valid_until: datetime


class Product(BaseModel):
    id: str
    commercial_name: str
    active_substance: str
    dose: str
    safety_period_days: int
    crop_type: str
    disease_code: str
    mapa_snapshot_date: datetime


class TelemetryCreate(BaseModel):
    telemetry_id: str = Field(min_length=1, max_length=120)
    parcel_id: str
    device_id: str = Field(min_length=1, max_length=120)
    temperature_c: float = Field(ge=-30, le=70)
    relative_humidity: float = Field(ge=0, le=100)
    leaf_wetness_hours: float = Field(ge=0, le=24)
    soil_moisture: float = Field(ge=0, le=100)
    battery_percent: float = Field(ge=0, le=100)
    measured_at: datetime
    owner_id: str | None = None


class DeviceCreate(BaseModel):
    parcel_id: str
    device_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    device_type: Literal['weather_station', 'leaf_sensor', 'soil_sensor']


class DeviceStateUpdate(BaseModel):
    active: bool


class Device(DeviceCreate):
    registered_at: datetime
    active: bool = True
    owner_id: str | None = None


class RiskSnapshot(BaseModel):
    parcel_id: str
    disease_code: str
    risk_score: float
    risk_level: str
    calculated_at: datetime
    owner_id: str | None = None


class Alert(BaseModel):
    id: int
    parcel_id: str
    owner_id: str
    disease_code: str
    alert_type: str
    risk_level: Literal["bajo", "medio", "alto"]
    risk_score: float = Field(ge=0, le=1)
    message: str
    created_at: datetime
    valid_until: datetime | None = None
    notified_at: datetime | None = None


class AlertUserState(BaseModel):
    alert_id: int
    read: bool
    acknowledged: bool
    read_at: datetime | None = None
    acknowledged_at: datetime | None = None


class AlertUserStateUpdate(BaseModel):
    read: bool | None = None
    acknowledged: bool | None = None


class NotificationDelivery(BaseModel):
    id: int
    alert_id: int
    status: str
    token_count: int
    sent_count: int
    failed_count: int
    created_at: datetime


class DeviceHealth(BaseModel):
    device_id: str
    parcel_id: str
    active: bool
    last_seen_at: datetime | None = None
    battery_percent: float | None = None
    telemetry_count: int


class WeatherEvidenceSummary(BaseModel):
    parcel_id: str
    available: bool
    source: str
    confidence: str
    station_count: int
    fresh_window_hours: int
    latest_observed_at: datetime | None = None
    stations: list[dict[str, object]]


class FieldReportSummary(BaseModel):
    parcel_id: str
    total_reports: int
    reports_by_type: dict[str, int]
    recent_reports_30d: int
    latest_reported_at: datetime | None = None
    latest_report_type: str | None = None


class ParcelAgronomicSummary(BaseModel):
    parcel_id: str
    label: str
    crop_type: str
    comarca: str
    device_count: int
    active_device_count: int
    latest_telemetry_at: datetime | None = None
    latest_battery_percent: float | None = None
    risk_count: int
    latest_risks: list[RiskSnapshot]
    recent_alert_count: int


class TelemetryQualityDevice(BaseModel):
    device_id: str
    name: str
    device_type: str
    active: bool
    latest_measured_at: datetime | None = None
    minutes_since_last_measurement: int | None = None
    sample_count: int


class TelemetryQualitySummary(BaseModel):
    parcel_id: str
    window_hours: int
    device_count: int
    active_device_count: int
    devices: list[TelemetryQualityDevice]


class ParcelActivityEvent(BaseModel):
    event_type: Literal["telemetry", "field_report", "alert", "risk_snapshot"]
    event_id: str
    event_at: datetime
    title: str
    detail: str | None = None


class CropCampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    crop_type: Literal["olivar", "vinedo"]
    started_at: datetime
    ended_at: datetime | None = None


class CropCampaignStatusUpdate(BaseModel):
    status: Literal["activa", "cerrada"]


class CropCampaign(BaseModel):
    id: str
    parcel_id: str
    owner_id: str
    name: str
    crop_type: Literal["olivar", "vinedo"]
    started_at: datetime
    ended_at: datetime | None = None
    status: Literal["activa", "cerrada"]


class IrrigationEventCreate(BaseModel):
    campaign_id: str | None = None
    started_at: datetime
    duration_minutes: int = Field(ge=1, le=1440)
    water_liters: float | None = Field(default=None, ge=0)
    method: Literal["goteo", "aspersion", "superficie", "otro"]
    notes: str | None = Field(default=None, max_length=1000)


class IrrigationEvent(BaseModel):
    id: str
    parcel_id: str
    campaign_id: str | None = None
    owner_id: str
    started_at: datetime
    duration_minutes: int
    water_liters: float | None = None
    method: Literal["goteo", "aspersion", "superficie", "otro"]
    notes: str | None = None


class TreatmentRecordCreate(BaseModel):
    campaign_id: str | None = None
    applied_at: datetime
    product_name: str = Field(min_length=1, max_length=200)
    active_substance: str | None = Field(default=None, max_length=200)
    dose: str | None = Field(default=None, max_length=120)
    treated_area_ha: float | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=1000)


class TreatmentRecord(BaseModel):
    id: str
    parcel_id: str
    campaign_id: str | None = None
    owner_id: str
    applied_at: datetime
    product_name: str
    active_substance: str | None = None
    dose: str | None = None
    treated_area_ha: float | None = None
    notes: str | None = None


class AlertPreferences(BaseModel):
    minimum_risk_level: Literal["medio", "alto"] = "medio"
    push_enabled: bool = True
    updated_at: datetime | None = None


class AlertPreferencesUpdate(BaseModel):
    minimum_risk_level: Literal["medio", "alto"] = "medio"
    push_enabled: bool = True


class IrrigationSummary(BaseModel):
    parcel_id: str
    campaign_id: str | None = None
    event_count: int
    total_duration_minutes: int
    total_water_liters: float
    events_with_volume: int


class AgronomicReport(BaseModel):
    parcel: dict[str, object]
    operational: dict[str, object]
    field_reports: dict[str, object]
    irrigation: dict[str, object]
    campaign_count: int
    treatment_count: int
