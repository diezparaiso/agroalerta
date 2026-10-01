from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings


class RiaIfapaClient:
    """Cliente para los agregados públicos diarios y mensuales de RIA/IFAPA.

    No implementa datos horarios: su disponibilidad y contrato no están confirmados.
    El llamador que inyecta un AsyncClient conserva la responsabilidad de cerrarlo.
    """

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        base_url: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = (base_url or settings.ria_base_url).rstrip("/")
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        """Cierra únicamente el cliente HTTP creado por esta instancia."""
        if self._owns_client:
            await self.client.aclose()

    @staticmethod
    def _validate_period(province: str, station: str, year: int, month_start: int, month_end: int) -> None:
        if not province.strip() or not station.strip():
            raise ValueError("La provincia y la estación son obligatorias")
        if not 1 <= year <= 9999:
            raise ValueError("El año debe estar entre 1 y 9999")
        if not 1 <= month_start <= 12 or not 1 <= month_end <= 12:
            raise ValueError("Los meses deben estar entre 1 y 12")
        if month_start > month_end:
            raise ValueError("El mes inicial no puede ser posterior al mes final")

    async def _get_aggregated_data(
        self,
        endpoint: str,
        province: str,
        station: str,
        year: int,
        month_start: int,
        month_end: int,
    ) -> Any:
        self._validate_period(province, station, year, month_start, month_end)
        province_path = quote(province.strip(), safe="")
        station_path = quote(station.strip(), safe="")
        url = (
            f"{self.base_url}/{endpoint}/{province_path}/{station_path}/"
            f"{year}/{month_start}/{month_end}"
        )
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_daily_data(
        self,
        province: str,
        station: str,
        year: int,
        month_start: int,
        month_end: int,
    ) -> Any:
        """Devuelve agregados diarios publicados por RIA/IFAPA."""
        return await self._get_aggregated_data(
            "datosdiarios", province, station, year, month_start, month_end
        )

    async def get_monthly_data(
        self,
        province: str,
        station: str,
        year: int,
        month_start: int,
        month_end: int,
    ) -> Any:
        """Devuelve agregados mensuales publicados por RIA/IFAPA."""
        return await self._get_aggregated_data(
            "datosmensuales", province, station, year, month_start, month_end
        )
