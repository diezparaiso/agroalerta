"""Cliente SIAR configurable.

El contrato HTTP concreto se configura explícitamente: no se presupone una ruta
ni un esquema que no se hayan confirmado con las credenciales/documentación del MAPA.
Sin endpoint configurado, SIAR queda desactivado y no aporta datos al sistema.
"""
from typing import Any
import httpx
from app.core.config import settings


class SiarNotConfiguredError(RuntimeError):
    """SIAR no está habilitado o falta configurar su ruta diaria."""


class SiarClient:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        base_url: str | None = None,
        daily_path: str | None = None,
        api_key: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (base_url if base_url is not None else settings.siar_base_url).rstrip("/")
        self.daily_path = daily_path if daily_path is not None else settings.siar_daily_path
        self.api_key = api_key if api_key is not None else settings.siar_api_key
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def get_daily_data(
        self, station: str, start_date: str, end_date: str
    ) -> Any | None:
        """Devuelve datos crudos; None significa que SIAR no está configurado."""
        if not self.base_url or not self.daily_path.strip():
            return None
        if not station.strip():
            raise ValueError("La estación SIAR es obligatoria")
        if start_date > end_date:
            raise ValueError("La fecha inicial no puede superar la fecha final")
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        path = self.daily_path.strip().lstrip("/")
        response = await self.client.get(
            f"{self.base_url}/{path}",
            params={"estacion": station.strip(), "fecha_inicio": start_date, "fecha_fin": end_date},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()
