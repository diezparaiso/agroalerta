from datetime import datetime, timedelta, timezone
import os
import logging
import time
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from app.domain.disease_rules import evaluate_risk
from app.domain.geospatial import haversine_km
from app.domain.raif_evidence import score_raif_evidence
from app.domain.weather_context import build_weather_context
from app.jobs.weather_ingestion_job import ingest_weather_for_parcel
from app.jobs.weather_refresh_job import refresh_all_parcel_weather
from app.connectors.source_registry import list_data_sources
from app.connectors.mapa_catalog import load_catalog
from app.core.config import settings
from app.core.storage import Storage
from app.schemas import Alert, AlertUserState, AlertUserStateUpdate, Device, DeviceCreate, DeviceHealth, DeviceStateUpdate, DiseaseRisk, FieldReportCreate, FieldReportSummary, NotificationDelivery, Parcel, WeatherEvidenceSummary, ParcelAgronomicSummary, ParcelCreate, Product, RiskSnapshot, TelemetryCreate, TelemetryQualitySummary, ParcelActivityEvent, CropCampaignCreate, CropCampaignStatusUpdate, CropCampaign, IrrigationEventCreate, IrrigationEvent, TreatmentRecordCreate, TreatmentRecord, AlertPreferences, AlertPreferencesUpdate
from app.core.security import optional_bearer_token
from app.schemas_push import PushTokenCreate


app = FastAPI(title="AgroAlerta Andalucia API", version="1.0.0")
logger = logging.getLogger('agroalerta.api')
request_metrics_data: dict[str, dict[str, float]] = {}
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware('http')
async def request_metrics(request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    metric = request_metrics_data.setdefault(request.url.path, {'count': 0, 'total_ms': 0})
    metric['count'] += 1
    metric['total_ms'] += elapsed_ms
    logger.info('request method=%s path=%s status=%s duration_ms=%.2f', request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.get('/health/metrics')
def metrics() -> dict[str, dict[str, float]]:
    return {path: {'count': values['count'], 'avg_ms': round(values['total_ms'] / values['count'], 2)} for path, values in request_metrics_data.items()}


storage = Storage()
products = load_catalog(settings.mapa_catalog_path) if settings.mapa_catalog_path else []


@app.get("/api/v1/data-sources")
def data_sources() -> list[dict[str, object]]:
    """Fuentes externas conocidas por AgroAlerta, sin exponer secretos."""
    return list_data_sources()


@app.get("/api/v1/data-sources/stats")
def data_source_stats() -> dict[str, object]:
    return {
        "raif_fitosanitario": {
            "records": storage.count_source_records("raif_fitosanitario"),
            "configured_crops": sorted(settings.raif_crop_urls),
        }
    }


@app.get("/health")
def health() -> dict[str, str]:
    try:
        storage.health()
        return {"status": "ok", "service": "agroalerta-api", "version": app.version}
    except Exception:
        return {"status": "degraded", "service": "agroalerta-api", "version": app.version}


@app.get("/health/integrations")
def integrations_health() -> dict[str, object]:
    from app.core.config import settings

    return {
        'aemet': {'configured': bool(settings.aemet_api_key), 'mode': 'live' if settings.aemet_api_key else 'fallback'},
        'ria_ifapa': {'configured': bool(settings.ria_base_url), 'mode': 'live'},
        'firebase_admin': {'configured': bool(os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')), 'mode': 'live' if os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON') else 'disabled'},
        'mapa': {'configured': False, 'mode': 'catalog-import'},
    }


@app.get("/api/v1/parcels", response_model=list[Parcel])
def list_parcels(_token: str | None = Depends(optional_bearer_token)) -> list[Parcel]:
    return storage.list_parcels(_token or 'anonymous')


@app.post("/api/v1/parcels", response_model=Parcel, status_code=status.HTTP_201_CREATED)
def create_parcel(payload: ParcelCreate, _token: str | None = Depends(optional_bearer_token)) -> Parcel:
    now = datetime.now(timezone.utc)
    parcel = Parcel(id=str(uuid4()), owner_id=_token or 'anonymous', created_at=now, updated_at=now, **payload.model_dump())
    return storage.create_parcel(parcel)


@app.get("/api/v1/parcels/{parcel_id}", response_model=Parcel)
def get_parcel(
    parcel_id: str,
    _token: str | None = Depends(optional_bearer_token),
) -> Parcel:
    owner_id = _token or "anonymous"
    parcel = storage.get_parcel(parcel_id, owner_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    return parcel


@app.put("/api/v1/parcels/{parcel_id}", response_model=Parcel)
def update_parcel(
    parcel_id: str,
    payload: ParcelCreate,
    expected_updated_at: datetime | None = Query(default=None),
    _token: str | None = Depends(optional_bearer_token),
) -> Parcel:
    owner_id = _token or 'anonymous'
    current = storage.get_parcel(parcel_id, owner_id)
    if current is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    if expected_updated_at is not None and current.updated_at != expected_updated_at:
        raise HTTPException(status_code=409, detail="La parcela ha cambiado desde la última lectura")
    parcel = storage.update_parcel(
        parcel_id,
        payload,
        owner_id,
        expected_updated_at=expected_updated_at,
    )
    if parcel is None:
        raise HTTPException(status_code=409, detail="La parcela ha cambiado durante la actualización")
    return parcel


@app.delete("/api/v1/parcels/{parcel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parcel(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> None:
    if not storage.delete_parcel(parcel_id, _token or 'anonymous'):
        raise HTTPException(status_code=404, detail="Parcela no encontrada")



@app.get("/api/v1/spatial-context/{parcel_id}")
def spatial_context(
    parcel_id: str,
    radius_km: float = Query(default=25, ge=1, le=100),
    _token: str | None = Depends(optional_bearer_token),
) -> dict[str, object]:
    """Devuelve evidencias georreferenciadas cercanas a una parcela."""
    owner_id = _token or 'anonymous'
    parcel = get_parcel(parcel_id, owner_id)
    matches: list[dict[str, object]] = []

    for source_code in ("raif_fitosanitario",):
        for record in storage.list_georeferenced_source_records(source_code):
            distance = haversine_km(
                parcel.latitude,
                parcel.longitude,
                float(record["latitude"]),
                float(record["longitude"]),
            )
            if distance <= radius_km:
                matches.append({
                    "source_code": record["source_code"],
                    "external_id": record["external_id"],
                    "distance_km": round(distance, 2),
                    "observed_at": record["observed_at"],
                    "province": record["province"],
                    "municipality": record["municipality"],
                    "parcel_reference": record["parcel_reference"],
                })

    matches.sort(key=lambda item: (item["distance_km"], item["observed_at"] or ""),)
    return {
        "parcel_id": parcel_id,
        "radius_km": radius_km,
        "evidence_count": len(matches),
        "evidence": matches[:100],
    }

@app.get("/api/v1/devices/{parcel_id}/health", response_model=list[DeviceHealth])
def device_health(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> list[DeviceHealth]:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    return [DeviceHealth(**item) for item in storage.list_device_health(parcel_id, owner_id)]


@app.get("/api/v1/weather-stations")
def get_weather_stations(_token=Depends(optional_bearer_token)):
    return {"source": "ria_ifapa", "stations": storage.list_weather_stations()}


@app.post("/api/v1/weather/refresh")
async def refresh_weather(_token: str | None = Depends(optional_bearer_token)) -> dict[str, object]:
    """Actualiza meteorología, recalcula riesgo y genera alertas del propietario."""
    owner_id = _token or "anonymous"
    return await refresh_all_parcel_weather(owner_id)


@app.post("/api/v1/weather/ingest/{parcel_id}")
async def ingest_parcel_weather(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> dict[str, object]:
    """Actualiza RIA para una parcela usando automáticamente estaciones cercanas."""
    owner_id = _token or 'anonymous'
    parcel = get_parcel(parcel_id, owner_id)
    result = await ingest_weather_for_parcel(parcel.latitude, parcel.longitude)
    return {"parcel_id": parcel_id, **result}


@app.get("/api/v1/weather-context/{parcel_id}")
def get_weather_context(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> dict[str, object]:
    owner_id = _token or 'anonymous'
    parcel = get_parcel(parcel_id, owner_id)
    context = build_weather_context(
        parcel.latitude,
        parcel.longitude,
        storage.list_latest_weather_observations(),
    )
    return {"parcel_id": parcel_id, **context}


@app.get("/api/v1/weather/{parcel_id}")
def get_weather(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> dict:
    owner_id = _token or 'anonymous'
    parcel = get_parcel(parcel_id, owner_id)
    context = build_weather_context(
        parcel.latitude,
        parcel.longitude,
        storage.list_latest_weather_observations(),
    )
    if context["available"]:
        return {
            "parcel_id": parcel_id,
            **context["weather"],
            "station_distance_km": context.get("station_distance_km"),
            "observed_at": context.get("observed_at"),
            "source": context.get("source"),
            "confidence": context.get("confidence"),
            "stations": context.get("stations", []),
        }
    return {
        "parcel_id": parcel_id,
        "temperature_c": None,
        "relative_humidity": None,
        "rainfall_mm_24h": None,
        "station_distance_km": None,
        "observed_at": None,
        "source": "none",
        "confidence": "no_disponible",
        "stations": [],
    }


@app.get("/api/v1/parcels/{parcel_id}/weather-evidence", response_model=WeatherEvidenceSummary)
def weather_evidence_summary(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> WeatherEvidenceSummary:
    owner_id = _token or "anonymous"
    parcel = get_parcel(parcel_id, owner_id)
    context = build_weather_context(
        parcel.latitude,
        parcel.longitude,
        storage.list_latest_weather_observations(),
    )
    return WeatherEvidenceSummary(
        parcel_id=parcel_id,
        available=bool(context["available"]),
        source=str(context["source"]),
        confidence=str(context["confidence"]),
        station_count=len(context.get("stations", [])),
        fresh_window_hours=72,
        latest_observed_at=context.get("observed_at"),
        stations=context.get("stations", []),
    )


@app.post("/api/v1/parcels/{parcel_id}/treatments", response_model=TreatmentRecord, status_code=201)
def create_treatment_record(
    parcel_id: str,
    payload: TreatmentRecordCreate,
    _token: str | None = Depends(optional_bearer_token),
) -> TreatmentRecord:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    applied_at = payload.applied_at if payload.applied_at.tzinfo else payload.applied_at.replace(tzinfo=timezone.utc)
    record = TreatmentRecord(
        id=str(uuid4()),
        parcel_id=parcel_id,
        campaign_id=payload.campaign_id,
        owner_id=owner_id,
        applied_at=applied_at,
        product_name=payload.product_name,
        active_substance=payload.active_substance,
        dose=payload.dose,
        treated_area_ha=payload.treated_area_ha,
        notes=payload.notes,
    )
    return TreatmentRecord(**storage.create_treatment_record(record.model_dump(mode="json")))


@app.get("/api/v1/parcels/{parcel_id}/treatments", response_model=list[TreatmentRecord])
def list_treatment_records(
    parcel_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    _token: str | None = Depends(optional_bearer_token),
) -> list[TreatmentRecord]:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    return [TreatmentRecord(**item) for item in storage.list_treatment_records(parcel_id, owner_id, limit)]


@app.post("/api/v1/parcels/{parcel_id}/irrigation", response_model=IrrigationEvent, status_code=201)
def create_irrigation_event(
    parcel_id: str,
    payload: IrrigationEventCreate,
    _token: str | None = Depends(optional_bearer_token),
) -> IrrigationEvent:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    if payload.started_at.tzinfo is None:
        started_at = payload.started_at.replace(tzinfo=timezone.utc)
    else:
        started_at = payload.started_at
    event = IrrigationEvent(
        id=str(uuid4()),
        parcel_id=parcel_id,
        campaign_id=payload.campaign_id,
        owner_id=owner_id,
        started_at=started_at,
        duration_minutes=payload.duration_minutes,
        water_liters=payload.water_liters,
        method=payload.method,
        notes=payload.notes,
    )
    return IrrigationEvent(**storage.create_irrigation_event(event.model_dump(mode="json")))


@app.get("/api/v1/parcels/{parcel_id}/irrigation", response_model=list[IrrigationEvent])
def list_irrigation_events(
    parcel_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    _token: str | None = Depends(optional_bearer_token),
) -> list[IrrigationEvent]:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    return [IrrigationEvent(**item) for item in storage.list_irrigation_events(parcel_id, owner_id, limit)]


@app.post("/api/v1/parcels/{parcel_id}/campaigns", response_model=CropCampaign, status_code=201)
def create_crop_campaign(parcel_id: str, payload: CropCampaignCreate, _token: str | None = Depends(optional_bearer_token)) -> CropCampaign:
    owner_id = _token or "anonymous"
    parcel = get_parcel(parcel_id, owner_id)
    if payload.ended_at is not None and payload.ended_at <= payload.started_at:
        raise HTTPException(status_code=422, detail="ended_at must be after started_at")
    campaign = CropCampaign(
        id=str(uuid4()),
        parcel_id=parcel.id,
        owner_id=owner_id,
        name=payload.name,
        crop_type=payload.crop_type,
        started_at=payload.started_at,
        ended_at=payload.ended_at,
        status="cerrada" if payload.ended_at is not None else "activa",
    )
    return CropCampaign(**storage.create_crop_campaign(campaign.model_dump(mode="json")))


@app.get("/api/v1/parcels/{parcel_id}/campaigns", response_model=list[CropCampaign])
def list_crop_campaigns(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> list[CropCampaign]:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    return [CropCampaign(**item) for item in storage.list_crop_campaigns(parcel_id, owner_id)]


@app.patch("/api/v1/campaigns/{campaign_id}/status", response_model=CropCampaign)
def update_crop_campaign_status(
    campaign_id: str,
    payload: CropCampaignStatusUpdate,
    _token: str | None = Depends(optional_bearer_token),
) -> CropCampaign:
    owner_id = _token or "anonymous"
    ended_at = datetime.now(timezone.utc).isoformat() if payload.status == "cerrada" else None
    campaign = storage.update_crop_campaign_status(campaign_id, owner_id, payload.status, ended_at)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return CropCampaign(**campaign)


@app.get("/api/v1/parcels/{parcel_id}/activity", response_model=list[ParcelActivityEvent])
def parcel_activity(
    parcel_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    _token: str | None = Depends(optional_bearer_token),
) -> list[ParcelActivityEvent]:
    """Devuelve una línea temporal de actividad persistida de la parcela."""
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    return [ParcelActivityEvent(**item) for item in storage.list_parcel_activity(parcel_id, owner_id, limit)]


@app.get("/api/v1/parcels/{parcel_id}/field-reports/summary", response_model=FieldReportSummary)
def field_report_summary(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> FieldReportSummary:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    return FieldReportSummary(**storage.field_report_summary(parcel_id, owner_id))


@app.get("/api/v1/parcels/{parcel_id}/agronomic-summary", response_model=ParcelAgronomicSummary)
def parcel_agronomic_summary(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> ParcelAgronomicSummary:
    owner_id = _token or "anonymous"
    parcel = get_parcel(parcel_id, owner_id)
    return ParcelAgronomicSummary(**storage.parcel_agronomic_summary(parcel, owner_id))


@app.get("/api/v1/disease-risk/{parcel_id}", response_model=list[DiseaseRisk])
def get_disease_risk(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> list[DiseaseRisk]:
    owner_id = _token or 'anonymous'
    parcel = get_parcel(parcel_id, owner_id)
    telemetry = storage.latest_telemetry(parcel_id, owner_id)
    raif_records = storage.list_georeferenced_source_records("raif_fitosanitario")
    weather_context = build_weather_context(
        parcel.latitude,
        parcel.longitude,
        storage.list_latest_weather_observations(),
    )
    risks = []
    for disease in ("repilo", "mildiu"):
        if not ((disease == "repilo" and parcel.crop_type == "olivar") or (disease == "mildiu" and parcel.crop_type == "vinedo")):
            continue
        evidence = score_raif_evidence(
            parcel.latitude,
            parcel.longitude,
            raif_records,
            disease,
        )
        risks.append(evaluate_risk(
            parcel_id,
            disease,
            parcel.crop_type,
            telemetry,
            raif_signal=float(evidence["signal"]),
            weather=weather_context["weather"] if weather_context["available"] else None,
        ))
    for risk in risks:
        storage.save_risk_snapshot(RiskSnapshot(parcel_id=parcel_id, owner_id=owner_id, disease_code=risk.disease_code, risk_score=risk.risk_score, risk_level=risk.risk_level, calculated_at=risk.calculated_at))
    return risks


@app.get("/api/v1/alert-preferences", response_model=AlertPreferences)
def get_alert_preferences(_token: str | None = Depends(optional_bearer_token)) -> AlertPreferences:
    owner_id = _token or "anonymous"
    current = storage.get_alert_preferences(owner_id)
    if current is None:
        return AlertPreferences()
    return AlertPreferences(
        minimum_risk_level=current["minimum_risk_level"],
        push_enabled=bool(current["push_enabled"]),
        updated_at=current["updated_at"],
    )


@app.put("/api/v1/alert-preferences", response_model=AlertPreferences)
def update_alert_preferences(
    payload: AlertPreferencesUpdate,
    _token: str | None = Depends(optional_bearer_token),
) -> AlertPreferences:
    owner_id = _token or "anonymous"
    saved = storage.set_alert_preferences(owner_id, payload.minimum_risk_level, payload.push_enabled)
    return AlertPreferences(
        minimum_risk_level=saved["minimum_risk_level"],
        push_enabled=bool(saved["push_enabled"]),
        updated_at=saved["updated_at"],
    )


@app.get("/api/v1/alerts", response_model=list[Alert])
def list_alerts(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    parcel_id: str | None = Query(default=None),
    _token: str | None = Depends(optional_bearer_token),
) -> list[Alert]:
    """Devuelve alertas persistidas; no recalcula riesgos ni crea eventos."""
    owner_id = _token or "anonymous"
    if parcel_id is not None:
        get_parcel(parcel_id, owner_id)
    return storage.list_alerts(
        parcel_id=parcel_id,
        owner_id=owner_id,
        limit=limit,
        offset=offset,
    )


@app.get("/api/v1/alerts/history", response_model=list[Alert])
def alert_history(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    parcel_id: str | None = Query(default=None),
    _token: str | None = Depends(optional_bearer_token),
) -> list[Alert]:
    owner_id = _token or "anonymous"
    if parcel_id is not None:
        get_parcel(parcel_id, owner_id)
    return storage.list_alerts(
        parcel_id=parcel_id,
        owner_id=owner_id,
        limit=limit,
        offset=offset,
    )


@app.get("/api/v1/risk-history/{parcel_id}", response_model=list[RiskSnapshot])
def risk_history(parcel_id: str, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0), _token: str | None = Depends(optional_bearer_token)) -> list[RiskSnapshot]:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    return storage.list_risk_snapshots(parcel_id, owner_id, limit, offset)


@app.get("/api/v1/products", response_model=list[Product])
def search_products(
    crop_type: str | None = Query(default=None),
    disease_code: str | None = Query(default=None),
) -> list[Product]:
    return [p for p in products if (not crop_type or p.crop_type == crop_type) and (not disease_code or p.disease_code == disease_code)]


@app.post("/api/v1/field-reports", status_code=status.HTTP_201_CREATED)
def create_report(payload: FieldReportCreate, _token: str | None = Depends(optional_bearer_token)) -> dict[str, str]:
    owner_id = _token or 'anonymous'
    get_parcel(payload.parcel_id, owner_id)
    payload = payload.model_copy(update={'owner_id': owner_id})
    report_id = payload.report_id or str(uuid4())
    created = storage.create_report(report_id, payload)
    return {"id": report_id, "status": "received" if created else "already_received"}


@app.post("/api/v1/telemetry", status_code=status.HTTP_202_ACCEPTED)
def ingest_telemetry(payload: TelemetryCreate, _token: str | None = Depends(optional_bearer_token)) -> dict[str, str]:
    owner_id = _token or 'anonymous'
    now = datetime.now(timezone.utc)
    measured_at = payload.measured_at
    if measured_at.tzinfo is None:
        measured_at = measured_at.replace(tzinfo=timezone.utc)
    if measured_at > now + timedelta(minutes=15):
        raise HTTPException(status_code=422, detail='Telemetría con fecha futura no válida')
    get_parcel(payload.parcel_id, owner_id)
    devices = storage.list_devices(payload.parcel_id, owner_id)
    device = next((item for item in devices if item.device_id == payload.device_id), None)
    if device is None:
        raise HTTPException(status_code=404, detail="Sensor no registrado en la parcela")
    if not device.active:
        raise HTTPException(status_code=409, detail="Sensor inactivo")
    payload = payload.model_copy(update={'owner_id': owner_id})
    created = storage.create_telemetry(payload)
    return {"status": "accepted" if created else "already_received", "device_id": payload.device_id, "telemetry_id": payload.telemetry_id}


@app.get("/api/v1/telemetry/{parcel_id}", response_model=TelemetryCreate)
def get_latest_telemetry(
    parcel_id: str,
    _token: str | None = Depends(optional_bearer_token),
) -> TelemetryCreate:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    telemetry = storage.latest_telemetry(parcel_id, owner_id)
    if telemetry is None:
        raise HTTPException(status_code=404, detail="Sin telemetria para esta parcela")
    return telemetry


@app.get("/api/v1/telemetry/{parcel_id}/quality", response_model=TelemetryQualitySummary)
def telemetry_quality(parcel_id: str, since_hours: int = Query(default=24, ge=1, le=168), _token: str | None = Depends(optional_bearer_token)) -> TelemetryQualitySummary:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    return TelemetryQualitySummary(**storage.telemetry_quality_summary(parcel_id, owner_id, since_hours))


@app.get("/api/v1/telemetry/{parcel_id}/history", response_model=list[dict])
def telemetry_history(
    parcel_id: str,
    limit: int = Query(default=200, ge=1, le=200),
    since_hours: int = Query(default=24, ge=1, le=168),
    device_id: str | None = Query(default=None, min_length=1),
    _token: str | None = Depends(optional_bearer_token),
) -> list[dict]:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    if device_id is not None:
        devices = storage.list_devices(parcel_id, owner_id)
        if not any(device.device_id == device_id for device in devices):
            raise HTTPException(status_code=404, detail="Sensor no encontrado")
    return storage.list_latest_telemetry(parcel_id, owner_id, limit, since_hours, device_id)


@app.post("/api/v1/devices", response_model=Device, status_code=status.HTTP_201_CREATED)
def register_device(payload: DeviceCreate, _token: str | None = Depends(optional_bearer_token)) -> Device:
    owner_id = _token or 'anonymous'
    get_parcel(payload.parcel_id, owner_id)
    device = Device(registered_at=datetime.now(timezone.utc), owner_id=owner_id, **payload.model_dump())
    return storage.create_device(device)


@app.get("/api/v1/devices/{parcel_id}", response_model=list[Device])
def list_devices(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> list[Device]:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    return storage.list_devices(parcel_id, owner_id)


@app.get("/api/v1/alerts/{alert_id}/state", response_model=AlertUserState)
def get_alert_user_state(alert_id: int, _token: str | None = Depends(optional_bearer_token)) -> AlertUserState:
    owner_id = _token or "anonymous"
    alert = next((item for item in storage.list_alerts(owner_id=owner_id, limit=500, offset=0) if item.id == alert_id), None)
    if alert is None: raise HTTPException(status_code=404, detail="Alerta no encontrada")
    state = storage.get_alert_user_state(owner_id, alert_id)
    return AlertUserState(alert_id=alert_id, read=bool(state and state['read_at']), acknowledged=bool(state and state['acknowledged_at']), read_at=state['read_at'] if state else None, acknowledged_at=state['acknowledged_at'] if state else None)

@app.patch("/api/v1/alerts/{alert_id}/state", response_model=AlertUserState)
def update_alert_user_state(alert_id: int, payload: AlertUserStateUpdate, _token: str | None = Depends(optional_bearer_token)) -> AlertUserState:
    owner_id = _token or "anonymous"
    alert = next((item for item in storage.list_alerts(owner_id=owner_id, limit=500, offset=0) if item.id == alert_id), None)
    if alert is None: raise HTTPException(status_code=404, detail="Alerta no encontrada")
    if payload.read is None and payload.acknowledged is None: raise HTTPException(status_code=422, detail='Debe indicar read o acknowledged')
    state = storage.set_alert_user_state(owner_id, alert_id, payload.read, payload.acknowledged)
    return AlertUserState(alert_id=alert_id, read=bool(state['read_at']), acknowledged=bool(state['acknowledged_at']), read_at=state['read_at'], acknowledged_at=state['acknowledged_at'])
@app.get("/api/v1/notifications/deliveries", response_model=list[NotificationDelivery])
def notification_delivery_history(
    alert_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=100, ge=1, le=200),
    _token: str | None = Depends(optional_bearer_token),
) -> list[NotificationDelivery]:
    owner_id = _token or "anonymous"
    return [NotificationDelivery(**item) for item in storage.list_notification_deliveries(owner_id, alert_id, limit)]


@app.post("/api/v1/push-tokens", status_code=status.HTTP_202_ACCEPTED)
def register_push_token(payload: PushTokenCreate, _token: str | None = Depends(optional_bearer_token)) -> dict[str, str]:
    payload = payload.model_copy(update={'owner_id': _token or 'anonymous'})
    storage.save_push_token(payload)
    return {'status': 'registered'}


@app.delete("/api/v1/push-tokens/{token}", status_code=status.HTTP_204_NO_CONTENT)
def unregister_push_token(token: str, _token: str | None = Depends(optional_bearer_token)) -> None:
    storage.delete_push_token(token, _token or 'anonymous')
