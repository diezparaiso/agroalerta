from datetime import datetime, timezone
from types import SimpleNamespace

from app.domain.activity_timeline import build_activity_timeline


def test_timeline_orders_activity_and_system_events() -> None:
    now = datetime.now(timezone.utc)
    activities = [SimpleNamespace(title="Riego", detail="1200 L", activity_type="irrigation", occurred_at=now)]
    risks = [SimpleNamespace(disease_code="repilo", risk_level="alto", risk_score=0.8, calculated_at=now)]
    telemetry = SimpleNamespace(measured_at=now, soil_moisture=34.0, relative_humidity=88.0)

    result = build_activity_timeline(activities, risks, telemetry)

    assert len(result) == 3
    assert {item["event_type"] for item in result} == {"actividad", "riesgo", "telemetria"}
