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
    parcel_id: str
    device_id: str = Field(min_length=1, max_length=120)
    temperature_c: float = Field(ge=-30, le=70)
    relative_humidity: float = Field(ge=0, le=100)
    leaf_wetness_hours: float = Field(ge=0, le=24)
    soil_moisture: float = Field(ge=0, le=100)
    rainfall_mm_24h: float = Field(default=0, ge=0, le=500)
    battery_percent: float = Field(ge=0, le=100)
    measured_at: datetime
    owner_id: str | None = None


class DeviceCreate(BaseModel):
    parcel_id: str
    device_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    device_type: Literal['weather_station', 'leaf_sensor', 'soil_sensor']


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
