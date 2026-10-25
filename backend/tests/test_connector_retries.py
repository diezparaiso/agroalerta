"""Pruebas de la política de reintentos de los conectores externos.

Regla acordada (2026-10-05): máximo 3 intentos (2 reintentos) con espera
creciente, solo ante timeout, 5xx y 429; el resto de errores no se reintentan.
"""

import asyncio

import httpx
import pytest

from app.connectors import http_retry
from app.connectors.http_retry import get_with_retries, is_retryable_error


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


class _FakeClient:
    """Cliente httpx mínimo: devuelve (o lanza) la secuencia de resultados."""

    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    async def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _response(status: int, url: str = 'https://fuente.example/datos', headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, request=httpx.Request('GET', url), headers=headers or {})


def test_timeout_is_retried_with_increasing_delay(sleeps: _SleepRecorder) -> None:
    client = _FakeClient([httpx.ReadTimeout('timeout'), httpx.ReadTimeout('timeout'), _response(200)])

    response = asyncio.run(get_with_retries(client, 'https://fuente.example/datos'))

    assert response.status_code == 200
    assert client.calls == 3
    assert sleeps.delays == [0.5, 1.0]


def test_server_error_is_retried(sleeps: _SleepRecorder) -> None:
    client = _FakeClient([_response(503), _response(200)])

    response = asyncio.run(get_with_retries(client, 'https://fuente.example/datos'))

    assert response.status_code == 200
    assert client.calls == 2
    assert sleeps.delays == [0.5]


def test_rate_limit_is_retried_and_honours_retry_after(sleeps: _SleepRecorder) -> None:
    client = _FakeClient([_response(429, headers={'retry-after': '2'}), _response(200)])

    response = asyncio.run(get_with_retries(client, 'https://fuente.example/datos'))

    assert response.status_code == 200
    assert client.calls == 2
    assert sleeps.delays == [2.0]


def test_client_error_is_not_retried(sleeps: _SleepRecorder) -> None:
    client = _FakeClient([_response(404)])

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(get_with_retries(client, 'https://fuente.example/datos'))

    assert client.calls == 1
    assert sleeps.delays == []


def test_gives_up_after_max_attempts(sleeps: _SleepRecorder) -> None:
    client = _FakeClient([httpx.ReadTimeout('timeout')])

    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(get_with_retries(client, 'https://fuente.example/datos'))

    assert client.calls == http_retry.MAX_ATTEMPTS
    assert len(sleeps.delays) == http_retry.MAX_ATTEMPTS - 1


def test_non_transient_transport_error_is_not_retried(sleeps: _SleepRecorder) -> None:
    client = _FakeClient([httpx.ConnectError('sin conexion')])

    with pytest.raises(httpx.ConnectError):
        asyncio.run(get_with_retries(client, 'https://fuente.example/datos'))

    assert client.calls == 1
    assert sleeps.delays == []


def test_is_retryable_error_classification() -> None:
    assert is_retryable_error(httpx.ReadTimeout('x'))
    assert is_retryable_error(httpx.ConnectTimeout('x'))
    assert is_retryable_error(httpx.HTTPStatusError('x', request=httpx.Request('GET', 'https://f'), response=_response(500)))
    assert is_retryable_error(httpx.HTTPStatusError('x', request=httpx.Request('GET', 'https://f'), response=_response(429)))
    assert not is_retryable_error(httpx.HTTPStatusError('x', request=httpx.Request('GET', 'https://f'), response=_response(404)))
    assert not is_retryable_error(httpx.ConnectError('x'))
    assert not is_retryable_error(ValueError('x'))
