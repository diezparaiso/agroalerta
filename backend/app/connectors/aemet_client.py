from typing import Any
import json

import httpx

from app.connectors.http_retry import get_with_retries
from app.core.config import settings


def _decode_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except (UnicodeDecodeError, json.JSONDecodeError):
        return json.loads(response.content.decode("iso-8859-15"))


class AemetClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=15)

    async def get_daily_forecast(self, municipality_code: str) -> Any:
        if not settings.aemet_api_key:
            raise RuntimeError("AEMET_API_KEY no configurada")
        response = await get_with_retries(
            self.client,
            f"{settings.aemet_base_url}/prediccion/especifica/municipio/diaria/{municipality_code}",
            headers={"api_key": settings.aemet_api_key},
        )
        metadata = _decode_json(response)
        data_url = metadata.get("datos") if isinstance(metadata, dict) else None
        if not data_url:
            raise RuntimeError("AEMET no devolvió una URL de datos")
        data_response = await get_with_retries(self.client, data_url)
        return _decode_json(data_response)

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()
