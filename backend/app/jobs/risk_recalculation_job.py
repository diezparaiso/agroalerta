from app.core.storage import Storage
from app.core.config import settings
from app.domain.disease_rules import evaluate_risk
from app.notifications.fcm_dispatcher import FcmDispatcher
from app.schemas import RiskSnapshot


def recalculate_risks() -> list[dict[str, str]]:
    """Recalcula las parcelas y devuelve eventos listos para enviar por FCM."""
    storage = Storage()
    storage.prune_risk_snapshots(settings.risk_snapshot_retention_days)
    dispatcher = FcmDispatcher()
    events: list[dict[str, str]] = []
    for parcel in storage.list_parcels():
        disease = 'repilo' if parcel.crop_type == 'olivar' else 'mildiu'
        previous = storage.list_risk_snapshots(parcel.id, parcel.owner_id)
        previous_level = next((item.risk_level for item in previous if item.disease_code == disease), None)
        risk = evaluate_risk(parcel.id, disease, parcel.crop_type)
        storage.save_risk_snapshot(RiskSnapshot(parcel_id=parcel.id, owner_id=parcel.owner_id, disease_code=risk.disease_code, risk_score=risk.risk_score, risk_level=risk.risk_level, calculated_at=risk.calculated_at))
        events.append({'parcel_id': parcel.id, 'disease': risk.disease_code, 'level': risk.risk_level})
        levels = {'bajo': 0, 'medio': 1, 'alto': 2}
        raised = previous_level is None or levels[risk.risk_level] > levels[previous_level]
        if risk.risk_level in {'medio', 'alto'} and raised:
            _, failed_tokens = dispatcher.send_risk_alert_to_tokens(storage.list_push_tokens(parcel.owner_id), risk.disease_code, parcel.label, risk.risk_level)
            for token in failed_tokens:
                storage.delete_push_token(token, parcel.owner_id)
    return events
