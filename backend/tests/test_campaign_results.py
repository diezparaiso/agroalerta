from datetime import datetime, timezone
from types import SimpleNamespace

from app.domain.campaign_results import build_campaign_result, build_results_summary
from app.schemas import CropCampaign


def make_campaign() -> CropCampaign:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return CropCampaign(
        id="camp-1", parcel_id="parcel-1", owner_id="owner-1", crop_type="olivar",
        season_label="2026", started_at=now, status="closed", target_yield_t_ha=4.0,
        created_at=now, updated_at=now,
    )


def test_campaign_result_calculates_yield_and_target_deviation() -> None:
    campaign = make_campaign()
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    result = build_campaign_result(
        campaign, "result-1", "owner-1",
        {
            "campaign_id": "camp-1",
            "harvested_at": now,
            "harvested_quantity_kg": 3600,
            "productive_area_ha": 1.0,
            "marketable_quantity_kg": 3000,
            "quality_grade": "A",
            "destination": "almazara",
            "notes": None,
        },
        now,
    )
    assert result.yield_kg_ha == 3600
    assert result.target_yield_kg_ha == 4000
    assert result.target_deviation_pct == -10


def test_results_summary_aggregates_production_and_operations() -> None:
    campaign = make_campaign()
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    results = [
        SimpleNamespace(harvested_quantity_kg=2000, marketable_quantity_kg=1800, productive_area_ha=1.0, harvested_at=now),
        SimpleNamespace(harvested_quantity_kg=1500, marketable_quantity_kg=1200, productive_area_ha=1.0, harvested_at=now),
    ]
    activities = [
        SimpleNamespace(activity_type="treatment", occurred_at=now),
        SimpleNamespace(activity_type="irrigation", occurred_at=now),
    ]
    summary = build_results_summary(campaign, results, activities, [{"id": "d1"}])
    assert summary["harvested_quantity_kg"] == 3500
    assert summary["marketable_quantity_kg"] == 3000
    assert summary["yield_kg_ha"] == 3500
    assert summary["target_deviation_pct"] == -12.5
    assert summary["treatment_count"] == 1
    assert summary["irrigation_count"] == 1
    assert summary["decision_count"] == 1
