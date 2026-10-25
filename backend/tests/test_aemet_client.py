import asyncio

import httpx
import pytest

from app.connectors import aemet_client, http_retry
from app.connectors.aemet_client import AemetClient, _load_json
from app.core import weather_service
from app.core.config import Settings


def test_load_json_decodes_charset_declared_by_aemet() -> None:
    # AEMET declara charset=ISO-8859-15 y sus textos llevan acentos
    # (verificado en vivo el 2026-10-01); decodificar como UTF-8 fallaria.
    body = '[{"productor": "Meteorología - AEMET. Gobierno de España"}]'.encode('iso-8859-15')
    response = httpx.Response(
        200,
        content=body,
        headers={'content-type': 'application/json;charset=ISO-8859-15'},
    )

    payload = _load_json(response)

    assert payload[0]['productor'] == 'Meteorología - AEMET. Gobierno de España'


class _SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> _SleepRecorder:
    recorder = _SleepRecorder()
    monkeypatch.setattr(http_retry, '_sleep', recorder)
    return recorder


def _client_with_handler(handler, monkeypatch: pytest.MonkeyPatch) -> AemetClient:
    """AemetClient sobre un transporte simulado y con clave de prueba."""
    monkeypatch.setattr(aemet_client, 'settings', Settings(aemet_api_key='clave-de-prueba'))
    transport = httpx.MockTransport(handler)
    return AemetClient(client=httpx.AsyncClient(transport=transport))


def test_aemet_client_retries_transient_500(sleeps: _SleepRecorder, monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {'meta': 0, 'data': 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if '/prediccion/especifica/municipio/diaria/' in str(request.url):
            attempts['meta'] += 1
            if attempts['meta'] == 1:
                return httpx.Response(500, text='fallo transitorio')
            return httpx.Response(200, json={'datos': 'https://opendata.aemet.es/opendata/api/datos/xyz'})
        attempts['data'] += 1
        return httpx.Response(
            200,
            content=b'[{"prediccion": {"dia": []}}]',
            headers={'content-type': 'application/json;charset=ISO-8859-15'},
        )

    client = _client_with_handler(handler, monkeypatch)
    payload = asyncio.run(client.get_daily_forecast('41091'))

    assert attempts == {'meta': 2, 'data': 1}
    assert sleeps.delays == [0.5]
    assert payload[0]['prediccion']['dia'] == []


def test_aemet_client_does_not_retry_client_errors(sleeps: _SleepRecorder, monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {'count': 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts['count'] += 1
        return httpx.Response(404, text='municipio desconocido')

    client = _client_with_handler(handler, monkeypatch)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(client.get_daily_forecast('00000'))

    assert attempts['count'] == 1
    assert sleeps.delays == []


def test_aemet_forecast_is_cached_per_municipality(monkeypatch: pytest.MonkeyPatch) -> None:
    """La predicción municipal se cachea para respetar la cuota de AEMET."""
    calls: list[str] = []

    class _FakeAemetClient:
        def __init__(self, client=None) -> None:
            pass

        async def get_daily_forecast(self, municipality_code: str):
            calls.append(municipality_code)
            return [{'prediccion': {'dia': [{'fecha': '2026-10-05'}]}}]

        async def aclose(self) -> None:
            pass

    monkeypatch.setattr(weather_service, 'AemetClient', _FakeAemetClient)
    weather_service._aemet_cache.clear()
    try:
        first = asyncio.run(weather_service._aemet_forecast('41091'))
        second = asyncio.run(weather_service._aemet_forecast('41091'))
        other = asyncio.run(weather_service._aemet_forecast('41039'))

        assert first == second
        assert calls == ['41091', '41039']
    finally:
        weather_service._aemet_cache.clear()
