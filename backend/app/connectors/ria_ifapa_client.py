from typing import Any

import httpx

from app.core.config import settings


class RiaIfapaClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=15)

    async def get_daily_data(
        self,
        province: str,
        station: str,
        year: int,
        month_start: int,
        month_end: int,
    ) -> Any:
        url = f'{settings.ria_base_url}/datosdiarios/{province}/{station}/{year}/{month_start}/{month_end}'
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()
