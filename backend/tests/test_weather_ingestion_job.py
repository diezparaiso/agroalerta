from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.jobs.weather_ingestion_job import ingest_weather


@pytest.mark.asyncio
async def test_ingest_weather_uses_current_month_when_window_is_omitted(monkeypatch: pytest.MonkeyPatch) -> None:
    aemet_forecast = AsyncMock(return_value=[])
    ria_daily = AsyncMock(return_value=[])

    monkeypatch.setattr("app.jobs.weather_ingestion_job.AemetClient.get_daily_forecast", aemet_forecast)
    monkeypatch.setattr("app.jobs.weather_ingestion_job.RiaIfapaClient.get_daily_data", ria_daily)
    monkeypatch.setattr(
        "app.jobs.weather_ingestion_job.datetime",
        type("FixedDatetime", (), {
            "now": staticmethod(lambda tz=None: datetime(2026, 9, 28, tzinfo=tz)),
        }),
    )

    result = await ingest_weather("41091", "Sevilla", "1")

    assert result["status"] == "ingested"
    assert result["year"] == "2026"
    assert result["month_start"] == "9"
    assert result["month_end"] == "9"
    ria_daily.assert_awaited_once_with("Sevilla", "1", 2026, 9, 9)


@pytest.mark.asyncio
async def test_ingest_weather_rejects_invalid_month_window() -> None:
    with pytest.raises(ValueError):
        await ingest_weather("41091", "Sevilla", "1", 2026, 13, 13)
