from datetime import date
from typing import Any

import httpx

from app.core.config import settings


class RiaIfapaClient:
    """Cliente de la Red de Informacion Agroclimatica de Andalucia (RIA-IFAPA).

    Endpoints oficiales verificados:
    - GET {ria_base_url}/estaciones
    - GET {ria_base_url}/datosdiarios/forceEt0/{provincia}/{estacion}/{desde}/{hasta}
    """

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=15)

    async def list_stations(self) -> list[Any]:
        response = await self.client.get(f'{settings.ria_base_url}/estaciones')
        response.raise_for_status()
        return response.json()

    async def get_daily_data(
        self,
        province: str,
        station: str,
        date_from: date,
        date_to: date,
    ) -> list[Any]:
        url = (
            f'{settings.ria_base_url}/datosdiarios/forceEt0/{province}/{station}'
            f'/{date_from.isoformat()}/{date_to.isoformat()}'
        )
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()
