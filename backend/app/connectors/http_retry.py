"""Reintentos limitados para consultas a servicios externos (timeouts y 5xx/429)."""
import asyncio
import httpx

async def get_with_retries(client: httpx.AsyncClient, url: str, *, headers: dict[str, str] | None = None) -> httpx.Response:
    last_error = None
    for attempt in range(3):
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            last_error = exc
            retryable = isinstance(exc, httpx.TimeoutException) or exc.response.status_code == 429 or exc.response.status_code >= 500
            if not retryable or attempt == 2:
                raise
            retry_after = exc.response.headers.get("retry-after") if isinstance(exc, httpx.HTTPStatusError) else None
            try:
                delay = min(30.0, max(0.5 * (2 ** attempt), float(retry_after))) if retry_after else 0.5 * (2 ** attempt)
            except ValueError:
                delay = 0.5 * (2 ** attempt)
            await asyncio.sleep(delay)
    raise last_error or RuntimeError("peticion sin intentos")
