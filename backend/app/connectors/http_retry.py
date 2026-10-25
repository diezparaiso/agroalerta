"""Reintentos limitados para las peticiones a fuentes externas.

Política acordada (2026-10-05): un máximo de 3 intentos (2 reintentos) con
espera creciente, y SOLO ante errores transitorios:

- timeout de conexión o de lectura (httpx.TimeoutException)
- respuesta 5xx (fallo del servidor remoto)
- respuesta 429 (límite de cuota alcanzado)

Cualquier otro fallo (400, 401, 404, errores de parseo...) se propaga
inmediatamente sin reintentar para no consumir cuota innecesariamente.
"""

import asyncio
from typing import Any, Callable

import httpx

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 0.5

# Permite que los tests sustituyan la espera real por una instantánea.
_sleep: Callable[[float], Any] = asyncio.sleep


def is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


def _retry_after_seconds(exc: httpx.HTTPStatusError) -> float | None:
    """Espera indicada por el servidor en 429/503, si viene en la cabecera."""
    value = exc.response.headers.get('retry-after')
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        return None
    return max(0.0, min(seconds, 30.0))


async def get_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """GET con hasta MAX_ATTEMPTS intentos y espera creciente.

    Devuelve la respuesta validada (raise_for_status ya aplicado) o lanza la
    última excepción. No reintentar ante errores no transitorios.
    """
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            if not is_retryable_error(exc) or attempt == MAX_ATTEMPTS - 1:
                raise
            last_error = exc
            delay = BACKOFF_BASE_SECONDS * (2 ** attempt)
            if isinstance(exc, httpx.HTTPStatusError):
                announced = _retry_after_seconds(exc)
                if announced is not None:
                    delay = max(delay, announced)
            await _sleep(delay)
    raise last_error if last_error else RuntimeError('peticion sin intentos')
