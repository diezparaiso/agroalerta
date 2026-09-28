from datetime import datetime, timezone
from types import SimpleNamespace

from app.domain.campaign_treatments import build_treatment_summary


def test_treatment_summary_counts_products_and_linked_decisions() -> None:
    now = datetime(2026, 8, 1, tzinfo=timezone.utc)
    campaign = SimpleNamespace(id="camp-1")
    treatments = [
        SimpleNamespace(product_name="Producto A", safety_period_days=14, disease_code="repilo", applied_at=now),
        SimpleNamespace(product_name="Producto A", safety_period_days=14, disease_code=None, applied_at=now),
        SimpleNamespace(product_name="Producto B", safety_period_days=7, disease_code="mildiu", applied_at=now),
    ]
    decisions = [
        {"disease_code": "repilo"},
        {"disease_code": "mildiu"},
    ]
    summary = build_treatment_summary(campaign, treatments, decisions)
    assert summary["treatment_count"] == 3
    assert summary["distinct_product_count"] == 2
    assert summary["treatment_days"] == 35
    assert summary["linked_decision_count"] == 2
    assert summary["latest_treatment_at"] == now
