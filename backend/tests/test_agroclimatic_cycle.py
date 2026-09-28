import pytest

from app.jobs import agroclimatic_cycle


@pytest.mark.asyncio
async def test_cycle_runs_sources_before_weather(monkeypatch):
    calls = []

    async def catalog():
        calls.append("catalog")
        return {"status": "synced"}

    async def raif(crop):
        calls.append(f"raif:{crop}")
        return {"status": "ingested", "crop": crop}

    async def weather(owner_id=None):
        calls.append("weather")
        return {"status": "completed"}

    monkeypatch.setattr(agroclimatic_cycle, "sync_ria_station_catalog", catalog)
    monkeypatch.setattr(agroclimatic_cycle, "ingest_raif", raif)
    monkeypatch.setattr(agroclimatic_cycle, "refresh_all_parcel_weather", weather)

    result = await agroclimatic_cycle.run_agroclimatic_cycle("owner-1")

    assert result["status"] == "completed"
    assert calls == ["catalog", "raif:olivar", "raif:vinedo", "weather"]
