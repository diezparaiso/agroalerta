import asyncio
import httpx
import pytest

from app.connectors.siar_client import SiarClient


def test_unconfigured_siar_returns_no_data_without_http_request():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(AssertionError("no debe consultar"))
        )) as http:
            client = SiarClient(client=http, base_url="", daily_path="")
            return await client.get_daily_data("A1", "2026-09-01", "2026-09-02")
    assert asyncio.run(run()) is None


def test_configured_siar_sends_query_and_optional_bearer_token():
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"observaciones": []})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = SiarClient(client=http, base_url="https://siar.example.test/", daily_path="/daily", api_key="secret")
            return await client.get_daily_data("Estación 1", "2026-09-01", "2026-09-02")
    assert asyncio.run(run()) == {"observaciones": []}
    assert seen[0].url.path == "/daily"
    assert seen[0].url.params["estacion"] == "Estación 1"
    assert seen[0].url.params["fecha_inicio"] == "2026-09-01"
    assert seen[0].headers["Authorization"] == "Bearer secret"


@pytest.mark.parametrize("args", [
    ("", "2026-09-01", "2026-09-02"),
    ("A1", "2026-09-03", "2026-09-02"),
])
def test_siar_rejects_invalid_station_or_period(args):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={}))) as http:
            client = SiarClient(client=http, base_url="https://siar.example.test", daily_path="daily")
            return await client.get_daily_data(*args)
    with pytest.raises(ValueError):
        asyncio.run(run())
