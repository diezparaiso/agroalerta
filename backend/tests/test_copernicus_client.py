import asyncio
import pytest

from app.connectors.copernicus_client import CopernicusClient, CopernicusNotConfiguredError


def test_copernicus_rejects_invalid_coordinates_before_network_access():
    client = CopernicusClient(api_key="", cds_client=object())
    with pytest.raises(ValueError, match="latitud"):
        asyncio.run(client.get_hourly_point(91, -5, "2026-09-01", "2026-09-02"))


def test_copernicus_rejects_impossible_dates():
    client = CopernicusClient(api_key="", cds_client=object())
    with pytest.raises(ValueError, match="fechas reales"):
        asyncio.run(client.get_hourly_point(37.4, -5.9, "2026-02-30", "2026-03-01"))


def test_copernicus_rejects_ranges_longer_than_seven_days():
    client = CopernicusClient(api_key="", cds_client=object())
    with pytest.raises(ValueError, match="7 días"):
        asyncio.run(client.get_hourly_point(37.4, -5.9, "2026-09-01", "2026-09-09"))


def test_copernicus_requires_api_key():
    client = CopernicusClient(api_key="", cds_client=None)
    with pytest.raises(CopernicusNotConfiguredError):
        client._client()
