from datetime import date
from typing import Any

import httpx

from app.connectors.http_retry import get_with_retries
from app.core.config import settings


class RiaIfapaClient:
    """Cliente para la Red de Información Agroclimática de Andalucía (IFAPA)."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=15)

    async def list_stations(self) -> list[Any]:
        response = await get_with_retries(self.client, f"{settings.ria_base_url}/estaciones")
        data = response.json()
        if not isinstance(data, list):
            raise ValueError("RIA-IFAPA no devolvió una lista de estaciones")
        return data

    async def get_daily_data(self, province: str, station: str, date_from: date, date_to: date) -> Any:
        url = (
            f"{settings.ria_base_url}/datosdiarios/forceEt0/{province}/{station}"
            f"/{date_from.isoformat()}/{date_to.isoformat()}"
        )
        response = await get_with_retries(self.client, url)
        return response.json()

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()
