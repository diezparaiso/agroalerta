from datetime import datetime, timezone

from app.domain.weather_context import build_weather_context


def test_builds_weighted_context_from_nearby_stations() -> None:
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    result = build_weather_context(
        37.3900,
        -5.9900,
        [
            {
                "source_code": "ria_ifapa",
                "station_code": "near",
                "latitude": 37.391,
                "longitude": -5.991,
                "observed_at": "2026-09-28T10:00:00+00:00",
                "temperature_c": 20,
                "relative_humidity": 80,
                "rainfall_mm_24h": 10,
                "confidence": "alta",
            },
            {
                "source_code": "ria_ifapa",
                "station_code": "second",
                "latitude": 37.42,
                "longitude": -5.99,
                "observed_at": "2026-09-28T09:00:00+00:00",
                "temperature_c": 22,
                "relative_humidity": 70,
                "rainfall_mm_24h": 6,
                "confidence": "alta",
            },
        ],
        now=now,
    )
    assert result["available"] is True
    assert result["source"] == "ria_ifapa"
    assert len(result["stations"]) == 2
    assert 20 <= float(result["weather"]["temperature_c"]) <= 22


def test_does_not_use_stale_weather() -> None:
    now = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)
    result = build_weather_context(
        37.3900,
        -5.9900,
        [{
            "source_code": "ria_ifapa",
            "station_code": "old",
            "latitude": 37.391,
            "longitude": -5.991,
            "observed_at": "2026-09-20T10:00:00+00:00",
            "temperature_c": 20,
        }],
        now=now,
    )
    assert result["available"] is False
