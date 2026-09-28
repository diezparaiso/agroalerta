from datetime import datetime, timezone
from types import SimpleNamespace

from app.domain.campaign_management import build_campaign_summary
from app.schemas import CropCampaign


def test_campaign_summary_keeps_operational_metrics() -> None:
    now = datetime.now(timezone.utc)
    campaign = CropCampaign(
        id="camp-1", parcel_id="parcel-1", owner_id="owner-1", crop_type="olivar",
        season_label="2026", started_at=now, status="active", created_at=now, updated_at=now,
    )
    activities = [
        SimpleNamespace(activity_type="treatment", quantity=1, occurred_at=now),
        SimpleNamespace(activity_type="harvest", quantity=3, occurred_at=now),
    ]
    decisions = [{"id": "d1", "campaign_id": "camp-1", "priority": "revisar"}]

    result = build_campaign_summary(campaign, activities, [], decisions)

    assert result["treatment_count"] == 1
    assert result["harvest_count"] == 1
    assert result["progress"] == "en_curso"
    assert len(decisions) == 1
