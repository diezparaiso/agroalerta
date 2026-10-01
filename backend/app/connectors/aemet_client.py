import json
from typing import Any

import httpx

from app.core.config import settings


def _load_json(response: httpx.Response) -> Any:
    """JSON de AEMET respetando el charset declarado.

    AEMET OpenData sirve sus cuerpos con charset=ISO-8859-15, no UTF-8
    (verificado en vivo el 2026-10-01); decodificar como UTF-8 falla con
    los acentos de los textos de la agencia.
    """
    try:
        text = response.text  # httpx usa el charset de la cabecera Content-Type
    except UnicodeDecodeError:
        text = response.content.decode('iso-8859-15')
    return json.loads(text)


class AemetClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=15)

    async def get_daily_forecast(self, municipality_code: str) -> Any:
        if not settings.aemet_api_key:
            raise RuntimeError('AEMET_API_KEY no configurada')
        response = await self.client.get(
            f'{settings.aemet_base_url}/prediccion/especifica/municipio/diaria/{municipality_code}',
            headers={'api_key': settings.aemet_api_key},
        )
        response.raise_for_status()
        metadata = _load_json(response)
        data_url = metadata.get('datos')
        if not data_url:
            raise RuntimeError('AEMET no devolvio una URL de datos')
        data_response = await self.client.get(data_url)
        data_response.raise_for_status()
        return _load_json(data_response)

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()
