from __future__ import annotations

import json
from datetime import datetime, timezone
from math import exp
from typing import Any

from app.domain.geospatial import haversine_km


def _date_decay(observed_at: str | None, now: datetime) -> float:
    if not observed_at:
        return 0.0
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
    except ValueError:
        return 0.0
    age_days = max(0.0, (now - observed).total_seconds() / 86400)
    return exp(-age_days / 14.0) if age_days <= 90 else 0.0


def _distance_decay(distance_km: float, scale_km: float = 15.0) -> float:
    return exp(-distance_km / scale_km)


def _matches_disease(payload: dict[str, Any], disease_code: str) -> bool:
    text = json.dumps(payload, ensure_ascii=False).lower()
    aliases = {
        "repilo": ("repilo", "spilocaea", "cycloconium"),
        "mildiu": ("mildiu", "plasmopara"),
    }
    return any(alias in text for alias in aliases.get(disease_code, (disease_code,)))


def score_raif_evidence(
    parcel_latitude: float,
    parcel_longitude: float,
    records: list[dict[str, object]],
    disease_code: str,
    now: datetime | None = None,
) -> dict[str, object]:
    """Calcula una señal de evidencia RAIF trazable, sin convertirla aún en diagnóstico."""
    reference_time = now or datetime.now(timezone.utc)
    contributions: list[dict[str, object]] = []

    for record in records:
        latitude = record.get("latitude")
        longitude = record.get("longitude")
        if latitude is None or longitude is None:
            continue
        payload = record.get("payload")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        if not isinstance(payload, dict) or not _matches_disease(payload, disease_code):
            continue

        distance_km = haversine_km(
            parcel_latitude,
            parcel_longitude,
            float(latitude),
            float(longitude),
        )
        temporal_weight = _date_decay(
            str(record.get("observed_at")) if record.get("observed_at") else None,
            reference_time,
        )
        spatial_weight = _distance_decay(distance_km)
        weight = temporal_weight * spatial_weight
        if weight <= 0:
            continue

        contributions.append({
            "external_id": record.get("external_id"),
            "distance_km": round(distance_km, 2),
            "observed_at": record.get("observed_at"),
            "weight": round(weight, 4),
        })

    contributions.sort(key=lambda item: float(item["weight"]), reverse=True)
    signal = min(1.0, sum(float(item["weight"]) for item in contributions) * 0.35)
    return {
        "signal": round(signal, 4),
        "evidence_count": len(contributions),
        "evidence": contributions[:20],
    }
