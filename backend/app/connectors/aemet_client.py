from typing import Any

import httpx

from app.core.config import settings


class AemetClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=15)

    async def get_daily_forecast(self, municipality_code: str) -> Any:
        if not settings.aemet_api_key:
            raise RuntimeError('AEMET_API_KEY no configurada')
        response = await self.client.get(
            f'{settings.aemet_base_url}/prediccion/especifica/municipio/diaria/{municipality_code}',
            headers={'api_key': settings.aemet_api_key},
        )
        response.raise_for_status()
        metadata = response.json()
        data_url = metadata.get('datos')
        if not data_url:
            raise RuntimeError('AEMET no devolvio una URL de datos')
        data_response = await self.client.get(data_url)
        data_response.raise_for_status()
        return data_response.json()
