from datetime import datetime, timezone
import os
import logging
import time
from typing import Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from app.domain.disease_rules import evaluate_risk
from app.core.storage import Storage
from app.schemas import Device, DeviceCreate, DiseaseRisk, FieldReportCreate, Parcel, ParcelCreate, Product, RiskSnapshot, TelemetryCreate
from app.core.security import optional_bearer_token
from app.schemas_push import PushTokenCreate
from app.api.sigpac import router as sigpac_router
from app.api.ria_ifapa import router as ria_ifapa_router
from app.api.siar import router as siar_router
from app.api.copernicus import router as copernicus_router


app = FastAPI(title="AgroAlerta Andalucia API", version="1.0.0")
app.include_router(sigpac_router)
app.include_router(ria_ifapa_router)
app.include_router(siar_router)
app.include_router(copernicus_router)
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
def metrics(_token: str | None = Depends(optional_bearer_token)) -> dict[str, dict[str, float]]:
    # Route-level request metrics can reveal internal traffic patterns. In production,
    # reuse the same Firebase-backed authentication policy as other protected routes.
    return {path: {'count': values['count'], 'avg_ms': round(values['total_ms'] / values['count'], 2)} for path, values in request_metrics_data.items()}


storage = Storage()
products = [
    Product(
        id="demo-copper-01",
        commercial_name="Catalogo MAPA pendiente de sincronizar",
        active_substance="Consultar registro oficial vigente",
        dose="Segun etiqueta autorizada",
        safety_period_days=0,
        crop_type="olivar",
        disease_code="repilo",
        mapa_snapshot_date=datetime.now(timezone.utc),
    )
]


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
        'copernicus_cds': {
            'configured': bool(settings.copernicus_api_key),
            'mode': 'configured_not_verified' if settings.copernicus_api_key else 'disabled',
            'live_connection_verified': False,
            'dataset': 'reanalysis-era5-single-levels',
        },
        'siar_mapa': {
            'configured': bool(settings.siar_base_url and settings.siar_daily_path),
            'mode': 'configured_not_verified' if settings.siar_base_url and settings.siar_daily_path else 'disabled',
            'live_connection_verified': False,
        },
        'ria_ifapa': {
            'configured': bool(settings.ria_base_url),
            'mode': 'configured_not_verified' if settings.ria_base_url else 'disabled',
            'live_connection_verified': False,
        },
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
def get_parcel(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> Parcel:
    owner_id = _token or "anonymous"
    parcel = storage.get_parcel(parcel_id, owner_id)
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    return parcel


@app.put("/api/v1/parcels/{parcel_id}", response_model=Parcel)
def update_parcel(parcel_id: str, payload: ParcelCreate, _token: str | None = Depends(optional_bearer_token)) -> Parcel:
    parcel = storage.update_parcel(parcel_id, payload, _token or 'anonymous')
    if parcel is None:
        raise HTTPException(status_code=404, detail="Parcela no encontrada")
    return parcel


@app.delete("/api/v1/parcels/{parcel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parcel(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> None:
    if not storage.delete_parcel(parcel_id, _token or 'anonymous'):
        raise HTTPException(status_code=404, detail="Parcela no encontrada")


@app.get("/api/v1/weather/{parcel_id}")
def get_weather(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> dict:
    get_parcel(parcel_id, _token or 'anonymous')
    raise HTTPException(
        status_code=503,
        detail="La integración meteorológica aún no proporciona observaciones verificadas para esta parcela.",
    )


@app.get("/api/v1/disease-risk/{parcel_id}", response_model=list[DiseaseRisk])
def get_disease_risk(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> list[DiseaseRisk]:
    owner_id = _token or 'anonymous'
    parcel = get_parcel(parcel_id, owner_id)
    telemetry = storage.latest_telemetry(parcel_id, owner_id)
    risks = [evaluate_risk(parcel_id, disease, parcel.crop_type, telemetry) for disease in ("repilo", "mildiu") if (disease == "repilo" and parcel.crop_type == "olivar") or (disease == "mildiu" and parcel.crop_type == "vinedo")]
    for risk in risks:
        storage.save_risk_snapshot(RiskSnapshot(parcel_id=parcel_id, owner_id=owner_id, disease_code=risk.disease_code, risk_score=risk.risk_score, risk_level=risk.risk_level, calculated_at=risk.calculated_at))
    return risks


@app.get("/api/v1/alerts", response_model=list[DiseaseRisk])
def list_alerts(_token: str | None = Depends(optional_bearer_token)) -> list[DiseaseRisk]:
    alerts: list[DiseaseRisk] = []
    for parcel in storage.list_parcels(_token or 'anonymous'):
        alerts.extend(get_disease_risk(parcel.id, _token))
    return alerts


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
    report_id = str(uuid4())
    storage.create_report(report_id, payload)
    return {"id": report_id, "status": "received"}


@app.post("/api/v1/telemetry", status_code=status.HTTP_202_ACCEPTED)
def ingest_telemetry(payload: TelemetryCreate, _token: str | None = Depends(optional_bearer_token)) -> dict[str, str]:
    owner_id = _token or 'anonymous'
    get_parcel(payload.parcel_id, owner_id)
    payload = payload.model_copy(update={'owner_id': owner_id})
    storage.create_telemetry(payload)
    return {"status": "accepted", "device_id": payload.device_id}


@app.get("/api/v1/telemetry/{parcel_id}", response_model=TelemetryCreate)
def get_latest_telemetry(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> TelemetryCreate:
    owner_id = _token or "anonymous"
    get_parcel(parcel_id, owner_id)
    telemetry = storage.latest_telemetry(parcel_id, owner_id)
    if telemetry is None:
        raise HTTPException(status_code=404, detail="Sin telemetria para esta parcela")
    return telemetry


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


@app.post("/api/v1/push-tokens", status_code=status.HTTP_202_ACCEPTED)
def register_push_token(payload: PushTokenCreate, _token: str | None = Depends(optional_bearer_token)) -> dict[str, str]:
    payload = payload.model_copy(update={'owner_id': _token or 'anonymous'})
    storage.save_push_token(payload)
    return {'status': 'registered'}


@app.delete("/api/v1/push-tokens/{token}", status_code=status.HTTP_204_NO_CONTENT)
def unregister_push_token(token: str, _token: str | None = Depends(optional_bearer_token)) -> None:
    storage.delete_push_token(token, _token or 'anonymous')
