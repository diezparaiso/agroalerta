from datetime import datetime, timezone

from app.core.storage import Storage


def test_weather_observation_persistence_uses_initialized_schema(tmp_path, monkeypatch):
    monkeypatch.setenv("AGROALERTA_DB_PATH", str(tmp_path / "agroalerta.db"))
    storage = Storage()

    storage.save_weather_observation(
        source_code="ria_ifapa",
        station_code="ST-01",
        observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        latitude=37.0,
        longitude=-4.0,
        temperature_c=12.5,
        relative_humidity=80.0,
        rainfall_mm_24h=4.2,
        confidence="alta",
    )

    observations = storage.list_weather_observations()
    assert len(observations) == 1
    assert observations[0]["station_code"] == "ST-01"
