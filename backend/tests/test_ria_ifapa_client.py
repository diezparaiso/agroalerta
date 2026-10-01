import asyncio

import httpx
import pytest

from app.connectors.ria_ifapa_client import RiaIfapaClient


def test_daily_data_uses_documented_endpoint_and_returns_json():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"datos": [{"fecha": "2026-09-01", "et0": 4.2}]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = RiaIfapaClient(client=http, base_url="https://ria.example.test/")
            return await client.get_daily_data("Sevilla", "Estacion 1", 2026, 1, 9)

    result = asyncio.run(run())
    assert result["datos"][0]["et0"] == 4.2
    assert seen == [
        "https://ria.example.test/datosdiarios/Sevilla/Estacion%201/2026/1/9"
    ]


def test_monthly_data_uses_monthly_endpoint():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"datos": []})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = RiaIfapaClient(client=http, base_url="https://ria.example.test")
            return await client.get_monthly_data("Córdoba", "A1", 2025, 2, 4)

    assert asyncio.run(run()) == {"datos": []}
    assert seen == ["/datosmensuales/C%C3%B3rdoba/A1/2025/2/4"]


@pytest.mark.parametrize(
    "args",
    [
        ("", "A1", 2026, 1, 2),
        ("Sevilla", "", 2026, 1, 2),
        ("Sevilla", "A1", 2026, 0, 2),
        ("Sevilla", "A1", 2026, 1, 13),
        ("Sevilla", "A1", 2026, 8, 2),
    ],
)
def test_invalid_query_period_is_rejected_before_http_request(args):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={})
            )
        ) as http:
            client = RiaIfapaClient(client=http, base_url="https://ria.example.test")
            with pytest.raises(ValueError):
                await client.get_daily_data(*args)

    asyncio.run(run())


def test_provider_http_errors_are_not_hidden():
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(503, json={"detail": "unavailable"})
            )
        ) as http:
            client = RiaIfapaClient(client=http, base_url="https://ria.example.test")
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_daily_data("Sevilla", "A1", 2026, 1, 1)

    asyncio.run(run())
