from datetime import datetime, timezone
import logging
import os
import time
from uuid import uuid4
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.security import optional_bearer_token
from app.core.storage import Storage
from app.core.weather_service import WeatherUnavailable, get_parcel_weather
from app.domain.disease_rules import evaluate_risk
from app.domain.agronomic_decision import make_agronomic_decision
from app.domain.farm_operation_center import build_farm_center
from app.domain.activity_timeline import build_activity_timeline
from app.domain.campaign_management import build_campaign_summary
from app.domain.campaign_results import build_campaign_result, build_results_summary
from app.domain.irrigation_intelligence import build_irrigation_intelligence
from app.schemas import AgronomicActivity, IrrigationEventCreate, IrrigationIntelligence, AgronomicActivityCreate, CampaignDecisionLink, CampaignResult, CampaignResultCreate, CampaignResultsSummary, CampaignStatusUpdate, CropCampaign, CropCampaignCreate, CampaignSummary, AgronomicDecision, Device, DeviceCreate, DiseaseRisk, FarmOperationCenter, FieldReportCreate, Parcel, ParcelCreate, Product, RiskSnapshot, TelemetryCreate
from app.schemas_push import PushTokenCreate


app = FastAPI(title="AgroAlerta Andalucia API", version="1.1.0")
logger = logging.getLogger('agroalerta.api')
request_metrics_data: dict[str, dict[str, float]] = {}


def _cors_origins() -> list[str]:
    configured = os.getenv('CORS_ALLOWED_ORIGINS', '').strip()
    if configured:
        return [origin.strip() for origin in configured.split(',') if origin.strip()]
    return ['http://localhost:3000', 'http://localhost:5000', 'http://localhost:8000']


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type'],
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
products = [
    Product(
        id='demo-copper-01',
        commercial_name='Catalogo MAPA pendiente de sincronizar',
        active_substance='Consultar registro oficial vigente',
        dose='Segun etiqueta autorizada',
        safety_period_days=0,
        crop_type='olivar',
        disease_code='repilo',
        mapa_snapshot_date=datetime.now(timezone.utc),
    )
]


@app.get('/health')
def health() -> dict[str, str]:
    try:
        storage.health()
        return {'status': 'ok', 'service': 'agroalerta-api', 'version': app.version}
    except Exception:
        return {'status': 'degraded', 'service': 'agroalerta-api', 'version': app.version}


@app.get('/health/integrations')
def integrations_health() -> dict[str, object]:
    from app.core.config import settings

    return {
        'aemet': {'configured': bool(settings.aemet_api_key), 'mode': 'live' if settings.aemet_api_key else 'fallback'},
        'ria_ifapa': {'configured': bool(settings.ria_base_url), 'mode': 'live'},
        'firebase_admin': {'configured': bool(os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')), 'mode': 'live' if os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON') else 'disabled'},
        'mapa': {'configured': False, 'mode': 'catalog-import'},
    }


@app.get('/api/v1/farm/center', response_model=FarmOperationCenter)
def farm_operation_center(_token: str | None = Depends(optional_bearer_token)) -> FarmOperationCenter:
    owner_id = _token or 'anonymous'
    parcels = storage.list_parcels(owner_id)
    states = []
    for parcel in parcels:
        telemetry = storage.latest_telemetry(parcel.id, owner_id)
        devices = storage.list_devices(parcel.id, owner_id)
        risks = get_disease_risk(parcel.id, _token)
        states.append({"parcel": parcel, "telemetry": telemetry, "devices": devices, "risks": risks})
    return FarmOperationCenter(**build_farm_center(parcels, states))


@app.get('/api/v1/parcels', response_model=list[Parcel])
def list_parcels(_token: str | None = Depends(optional_bearer_token)) -> list[Parcel]:
    return storage.list_parcels(_token or 'anonymous')


@app.post('/api/v1/parcels', response_model=Parcel, status_code=status.HTTP_201_CREATED)
def create_parcel(payload: ParcelCreate, _token: str | None = Depends(optional_bearer_token)) -> Parcel:
    now = datetime.now(timezone.utc)
    parcel = Parcel(id=str(uuid4()), owner_id=_token or 'anonymous', created_at=now, updated_at=now, **payload.model_dump())
    return storage.create_parcel(parcel)



@app.post('/api/v1/parcels/{parcel_id}/campaigns', response_model=CropCampaign, status_code=status.HTTP_201_CREATED)
def create_campaign(parcel_id: str, payload: CropCampaignCreate, _token: str | None = Depends(optional_bearer_token)) -> CropCampaign:
    owner_id = _token or 'anonymous'
    parcel = get_parcel(parcel_id, owner_id)
    if payload.parcel_id != parcel_id:
        raise HTTPException(status_code=400, detail='La campaña no pertenece a la parcela indicada')
    if payload.crop_type != parcel.crop_type:
        raise HTTPException(status_code=400, detail='El cultivo de la campaña no coincide con la parcela')
    if payload.ended_at and payload.ended_at < payload.started_at:
        raise HTTPException(status_code=400, detail='La fecha de fin no puede ser anterior al inicio')
    if payload.status == 'active':
        active = [item for item in storage.list_campaigns(parcel_id, owner_id) if item.status == 'active']
        if active:
            raise HTTPException(status_code=409, detail='La parcela ya tiene una campaña activa')
    payload = payload.model_copy(update={'owner_id': owner_id})
    return storage.create_campaign(str(uuid4()), payload)


@app.get('/api/v1/parcels/{parcel_id}/campaigns', response_model=list[CropCampaign])
def list_campaigns(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> list[CropCampaign]:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    return storage.list_campaigns(parcel_id, owner_id)


@app.patch('/api/v1/campaigns/{campaign_id}/status', response_model=CropCampaign)
def update_campaign_status(campaign_id: str, payload: CampaignStatusUpdate, _token: str | None = Depends(optional_bearer_token)) -> CropCampaign:
    owner_id = _token or 'anonymous'
    campaign = storage.get_campaign(campaign_id, owner_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail='Campaña no encontrada')
    ended_at = payload.ended_at
    if payload.status == 'closed' and ended_at is None:
        ended_at = datetime.now(timezone.utc)
    if ended_at and ended_at < campaign.started_at:
        raise HTTPException(status_code=400, detail='La fecha de fin no puede ser anterior al inicio')
    if payload.status == 'active':
        active = [item for item in storage.list_campaigns(campaign.parcel_id, owner_id) if item.status == 'active' and item.id != campaign_id]
        if active:
            raise HTTPException(status_code=409, detail='La parcela ya tiene otra campaña activa')
    updated = storage.update_campaign_status(campaign_id, owner_id, payload.status, ended_at)
    if updated is None:
        raise HTTPException(status_code=404, detail='Campaña no encontrada')
    return updated


@app.get('/api/v1/campaigns/{campaign_id}/summary', response_model=CampaignSummary)
def campaign_summary(campaign_id: str, _token: str | None = Depends(optional_bearer_token)) -> CampaignSummary:
    owner_id = _token or 'anonymous'
    campaign = storage.get_campaign(campaign_id, owner_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail='Campaña no encontrada')
    activities = storage.list_activities(campaign.parcel_id, owner_id, 300)
    risks = get_disease_risk(campaign.parcel_id, _token)
    return CampaignSummary(**build_campaign_summary(campaign, activities, risks, storage.list_campaign_decisions(campaign_id, owner_id)))


@app.post('/api/v1/parcels/{parcel_id}/activities', response_model=AgronomicActivity, status_code=status.HTTP_201_CREATED)
def create_activity(parcel_id: str, payload: AgronomicActivityCreate, _token: str | None = Depends(optional_bearer_token)) -> AgronomicActivity:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    if payload.parcel_id != parcel_id:
        raise HTTPException(status_code=400, detail='La actividad no pertenece a la parcela indicada')
    payload = payload.model_copy(update={'owner_id': owner_id})
    return storage.create_activity(str(uuid4()), payload)


@app.get('/api/v1/parcels/{parcel_id}/activity-timeline')
def activity_timeline(parcel_id: str, limit: int = Query(default=100, ge=1, le=300), _token: str | None = Depends(optional_bearer_token)) -> list[dict]:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    return build_activity_timeline(
        storage.list_activities(parcel_id, owner_id, limit),
        get_disease_risk(parcel_id, _token),
        storage.latest_telemetry(parcel_id, owner_id),
        limit,
    )


@app.post('/api/v1/parcels/{parcel_id}/irrigation/events', status_code=status.HTTP_201_CREATED)
def create_irrigation_event(parcel_id: str, payload: IrrigationEventCreate, _token: str | None = Depends(optional_bearer_token)) -> dict:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    if payload.parcel_id != parcel_id:
        raise HTTPException(status_code=400, detail='El riego no pertenece a la parcela indicada')
    event = {'id': str(uuid4()), **payload.model_dump(mode='json'), 'owner_id': owner_id}
    storage.create_irrigation_event(event)
    return event

@app.get('/api/v1/parcels/{parcel_id}/irrigation/events')
def list_irrigation_events(parcel_id: str, limit: int = Query(default=100, ge=1, le=200), _token: str | None = Depends(optional_bearer_token)) -> list[dict]:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    return storage.list_irrigation_events(parcel_id, owner_id, limit)

@app.get('/api/v1/parcels/{parcel_id}/irrigation/intelligence', response_model=IrrigationIntelligence)
def irrigation_intelligence(parcel_id: str, window_days: int = Query(default=7, ge=1, le=90), _token: str | None = Depends(optional_bearer_token)) -> IrrigationIntelligence:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    telemetry = storage.latest_telemetry(parcel_id, owner_id)
    return IrrigationIntelligence(**build_irrigation_intelligence(parcel_id, storage.list_irrigation_events(parcel_id, owner_id, 200), telemetry.model_dump(mode='json') if telemetry else None, window_days))

@app.get('/api/v1/parcels/{parcel_id}', response_model=Parcel)
def get_parcel(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> Parcel:
    parcel = storage.get_parcel(parcel_id, _token or 'anonymous')
    if parcel is None:
        raise HTTPException(status_code=404, detail='Parcela no encontrada')
    return parcel


@app.put('/api/v1/parcels/{parcel_id}', response_model=Parcel)
def update_parcel(parcel_id: str, payload: ParcelCreate, _token: str | None = Depends(optional_bearer_token)) -> Parcel:
    parcel = storage.update_parcel(parcel_id, payload, _token or 'anonymous')
    if parcel is None:
        raise HTTPException(status_code=404, detail='Parcela no encontrada')
    return parcel


@app.delete('/api/v1/parcels/{parcel_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_parcel(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> None:
    if not storage.delete_parcel(parcel_id, _token or 'anonymous'):
        raise HTTPException(status_code=404, detail='Parcela no encontrada')


@app.get('/api/v1/weather/{parcel_id}')
async def get_weather(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> dict:
    parcel = get_parcel(parcel_id, _token)
    try:
        return await get_parcel_weather(parcel)
    except WeatherUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@app.get('/api/v1/disease-risk/{parcel_id}', response_model=list[DiseaseRisk])
def get_disease_risk(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> list[DiseaseRisk]:
    owner_id = _token or 'anonymous'
    parcel = get_parcel(parcel_id, owner_id)
    telemetry = storage.latest_telemetry(parcel_id, owner_id)
    risks = [evaluate_risk(parcel_id, disease, parcel.crop_type, telemetry) for disease in ('repilo', 'mildiu') if (disease == 'repilo' and parcel.crop_type == 'olivar') or (disease == 'mildiu' and parcel.crop_type == 'vinedo')]
    for risk in risks:
        storage.save_risk_snapshot(RiskSnapshot(parcel_id=parcel_id, owner_id=owner_id, disease_code=risk.disease_code, risk_score=risk.risk_score, risk_level=risk.risk_level, calculated_at=risk.calculated_at))
    return risks


@app.get('/api/v1/agronomic-decision/{parcel_id}/{disease_code}', response_model=AgronomicDecision)
def agronomic_decision(parcel_id: str, disease_code: Literal["repilo", "mildiu"], campaign_id: str | None = Query(default=None), _token: str | None = Depends(optional_bearer_token)) -> AgronomicDecision:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, _token)
    risks = get_disease_risk(parcel_id, _token)
    risk = next((item for item in risks if item.disease_code == disease_code), None)
    if risk is None:
        raise HTTPException(status_code=404, detail="Riesgo no disponible para el cultivo")
    telemetry = storage.latest_telemetry(parcel_id, owner_id)
    decision = AgronomicDecision(**make_agronomic_decision(
        parcel_id,
        disease_code,
        risk.model_dump(mode='json'),
        telemetry.model_dump(mode='json') if telemetry else None,
    ))
    if campaign_id is not None:
        campaign = storage.get_campaign(campaign_id, owner_id)
        if campaign is None or campaign.parcel_id != parcel_id:
            raise HTTPException(status_code=404, detail='Campaña no encontrada para la parcela')
        storage.create_campaign_decision(str(uuid4()), campaign_id, owner_id, decision.model_dump(mode='json'))
    return decision




@app.post('/api/v1/campaigns/{campaign_id}/results', response_model=CampaignResult, status_code=status.HTTP_201_CREATED)
def create_campaign_result(campaign_id: str, payload: CampaignResultCreate, _token: str | None = Depends(optional_bearer_token)) -> CampaignResult:
    owner_id = _token or 'anonymous'
    campaign = storage.get_campaign(campaign_id, owner_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail='Campaña no encontrada')
    if payload.campaign_id != campaign_id:
        raise HTTPException(status_code=400, detail='El resultado no pertenece a la campaña indicada')
    if payload.harvested_at < campaign.started_at:
        raise HTTPException(status_code=400, detail='La cosecha no puede ser anterior al inicio de la campaña')
    if campaign.ended_at and payload.harvested_at > campaign.ended_at:
        raise HTTPException(status_code=400, detail='La cosecha queda fuera del periodo de campaña')
    now = datetime.now(timezone.utc)
    result = build_campaign_result(campaign, str(uuid4()), owner_id, payload.model_dump(), now)
    storage.create_campaign_result(result.id, campaign_id, owner_id, {**result.model_dump(), 'created_at': now})
    return result


@app.get('/api/v1/campaigns/{campaign_id}/results', response_model=list[CampaignResult])
def list_campaign_results(campaign_id: str, _token: str | None = Depends(optional_bearer_token)) -> list[CampaignResult]:
    owner_id = _token or 'anonymous'
    campaign = storage.get_campaign(campaign_id, owner_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail='Campaña no encontrada')
    return [CampaignResult(**item) for item in storage.list_campaign_results(campaign_id, owner_id)]


@app.get('/api/v1/campaigns/{campaign_id}/results/summary', response_model=CampaignResultsSummary)
def campaign_results_summary(campaign_id: str, _token: str | None = Depends(optional_bearer_token)) -> CampaignResultsSummary:
    owner_id = _token or 'anonymous'
    campaign = storage.get_campaign(campaign_id, owner_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail='Campaña no encontrada')
    results = [CampaignResult(**item) for item in storage.list_campaign_results(campaign_id, owner_id)]
    activities = storage.list_activities(campaign.parcel_id, owner_id, 300)
    decisions = storage.list_campaign_decisions(campaign_id, owner_id)
    return CampaignResultsSummary(**build_results_summary(campaign, results, activities, decisions))


@app.get('/api/v1/campaigns/{campaign_id}/decisions', response_model=list[CampaignDecisionLink])
def campaign_decisions(campaign_id: str, _token: str | None = Depends(optional_bearer_token)) -> list[CampaignDecisionLink]:
    owner_id = _token or 'anonymous'
    campaign = storage.get_campaign(campaign_id, owner_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail='Campaña no encontrada')
    return [CampaignDecisionLink(**item) for item in storage.list_campaign_decisions(campaign_id, owner_id)]


@app.get('/api/v1/alerts', response_model=list[DiseaseRisk])
def list_alerts(_token: str | None = Depends(optional_bearer_token)) -> list[DiseaseRisk]:
    alerts: list[DiseaseRisk] = []
    for parcel in storage.list_parcels(_token or 'anonymous'):
        alerts.extend(get_disease_risk(parcel.id, _token))
    return alerts


@app.get('/api/v1/risk-history/{parcel_id}', response_model=list[RiskSnapshot])
def risk_history(parcel_id: str, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0), _token: str | None = Depends(optional_bearer_token)) -> list[RiskSnapshot]:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    return storage.list_risk_snapshots(parcel_id, owner_id, limit, offset)


@app.get('/api/v1/products', response_model=list[Product])
def search_products(crop_type: str | None = Query(default=None), disease_code: str | None = Query(default=None)) -> list[Product]:
    return [p for p in products if (not crop_type or p.crop_type == crop_type) and (not disease_code or p.disease_code == disease_code)]


@app.post('/api/v1/field-reports', status_code=status.HTTP_201_CREATED)
def create_report(payload: FieldReportCreate, _token: str | None = Depends(optional_bearer_token)) -> dict[str, str]:
    owner_id = _token or 'anonymous'
    get_parcel(payload.parcel_id, owner_id)
    payload = payload.model_copy(update={'owner_id': owner_id})
    report_id = str(uuid4())
    storage.create_report(report_id, payload)
    return {'id': report_id, 'status': 'received'}


@app.post('/api/v1/telemetry', status_code=status.HTTP_202_ACCEPTED)
def ingest_telemetry(payload: TelemetryCreate, _token: str | None = Depends(optional_bearer_token)) -> dict[str, str]:
    owner_id = _token or 'anonymous'
    get_parcel(payload.parcel_id, owner_id)
    payload = payload.model_copy(update={'owner_id': owner_id})
    storage.create_telemetry(payload)
    return {'status': 'accepted', 'device_id': payload.device_id}


@app.get('/api/v1/telemetry/{parcel_id}', response_model=TelemetryCreate)
def get_latest_telemetry(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> TelemetryCreate:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    telemetry = storage.latest_telemetry(parcel_id, owner_id)
    if telemetry is None:
        raise HTTPException(status_code=404, detail='Sin telemetria para esta parcela')
    return telemetry


@app.post('/api/v1/devices', response_model=Device, status_code=status.HTTP_201_CREATED)
def register_device(payload: DeviceCreate, _token: str | None = Depends(optional_bearer_token)) -> Device:
    owner_id = _token or 'anonymous'
    get_parcel(payload.parcel_id, owner_id)
    device = Device(registered_at=datetime.now(timezone.utc), owner_id=owner_id, **payload.model_dump())
    return storage.create_device(device)


@app.get('/api/v1/devices/{parcel_id}', response_model=list[Device])
def list_devices(parcel_id: str, _token: str | None = Depends(optional_bearer_token)) -> list[Device]:
    owner_id = _token or 'anonymous'
    get_parcel(parcel_id, owner_id)
    return storage.list_devices(parcel_id, owner_id)


@app.post('/api/v1/push-tokens', status_code=status.HTTP_202_ACCEPTED)
def register_push_token(payload: PushTokenCreate, _token: str | None = Depends(optional_bearer_token)) -> dict[str, str]:
    payload = payload.model_copy(update={'owner_id': _token or 'anonymous'})
    storage.save_push_token(payload)
    return {'status': 'registered'}


@app.delete('/api/v1/push-tokens/{token}', status_code=status.HTTP_204_NO_CONTENT)
def unregister_push_token(token: str, _token: str | None = Depends(optional_bearer_token)) -> None:
    owner_id = _token or 'anonymous'
    storage.delete_push_token(token, owner_id)
