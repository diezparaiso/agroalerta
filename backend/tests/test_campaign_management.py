from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.domain.campaign_management import build_campaign_summary
from app.schemas import CropCampaign


def campaign() -> CropCampaign:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return CropCampaign(
        id="camp-1",
        parcel_id="parcel-1",
        owner_id="owner-1",
        crop_type="olivar",
        season_label="2026",
        started_at=start,
        status="active",
        created_at=start,
        updated_at=start,
    )


def test_campaign_summary_aggregates_activity_types_and_risk() -> None:
    start = campaign().started_at
    activities = [
        SimpleNamespace(activity_type="irrigation", quantity=1200, occurred_at=start + timedelta(days=2)),
        SimpleNamespace(activity_type="irrigation", quantity=800, occurred_at=start + timedelta(days=3)),
        SimpleNamespace(activity_type="treatment", quantity=None, occurred_at=start + timedelta(days=4)),
        SimpleNamespace(activity_type="observation", quantity=None, occurred_at=start + timedelta(days=5)),
        SimpleNamespace(activity_type="harvest", quantity=4, occurred_at=start + timedelta(days=6)),
        SimpleNamespace(activity_type="labor", quantity=None, occurred_at=start + timedelta(days=7)),
    ]
    risks = [
        SimpleNamespace(risk_level="medio", calculated_at=start + timedelta(days=3)),
        SimpleNamespace(risk_level="alto", calculated_at=start + timedelta(days=5)),
    ]

    result = build_campaign_summary(campaign(), activities, risks)

    assert result["activity_count"] == 6
    assert result["irrigation_count"] == 2
    assert result["irrigation_quantity"] == 2000
    assert result["treatment_count"] == 1
    assert result["observation_count"] == 1
    assert result["harvest_count"] == 1
    assert result["highest_risk"] == "alto"
    assert result["progress"] == "en_curso"


def test_campaign_summary_excludes_activity_outside_campaign_window() -> None:
    campaign_item = campaign()
    activities = [
        SimpleNamespace(activity_type="irrigation", quantity=500, occurred_at=campaign_item.started_at - timedelta(days=1)),
    ]

    result = build_campaign_summary(campaign_item, activities, [])

    assert result["activity_count"] == 0
    assert result["irrigation_quantity"] == 0
    assert result["latest_activity_at"] is None
