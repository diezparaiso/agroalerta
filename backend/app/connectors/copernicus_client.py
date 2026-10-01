"""Acceso controlado al Climate Data Store (Copernicus).

Usa el cliente oficial cdsapi. La solicitud y las variables deben ajustarse
al formulario/API code del dataset elegido; nunca se marca como verificado
un resultado obtenido mediante transporte simulado.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
import asyncio

from app.core.config import settings


DATASET = "reanalysis-era5-single-levels"
VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "total_precipitation",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
]


class CopernicusNotConfiguredError(RuntimeError):
    """Falta la clave personal del Climate Data Store."""


class CopernicusClient:
    def __init__(self, api_url: str | None = None, api_key: str | None = None, cds_client: Any = None):
        self.api_url = api_url if api_url is not None else settings.copernicus_api_url
        self.api_key = api_key if api_key is not None else settings.copernicus_api_key
        self._cds_client = cds_client

    def _client(self):
        if not self.api_key:
            raise CopernicusNotConfiguredError("Falta COPERNICUS_API_KEY")
        if self._cds_client is None:
            try:
                import cdsapi
            except ImportError as exc:
                raise RuntimeError("Falta instalar la dependencia cdsapi") from exc
            self._cds_client = cdsapi.Client(url=self.api_url, key=self.api_key, quiet=True)
        return self._cds_client

    async def get_hourly_point(
        self, latitude: float, longitude: float, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Obtiene ERA5 horario y extrae el píxel más próximo a una coordenada."""
        if not -90 <= latitude <= 90:
            raise ValueError("La latitud debe estar entre -90 y 90")
        if not -180 <= longitude <= 180:
            raise ValueError("La longitud debe estar entre -180 y 180")
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as exc:
            raise ValueError("Las fechas deben ser fechas reales en formato YYYY-MM-DD") from exc
        if end < start:
            raise ValueError("La fecha inicial no puede superar la fecha final")
        if (end - start).days > 6:
            raise ValueError("El intervalo máximo por consulta es de 7 días")
        return await asyncio.to_thread(self._retrieve_point, latitude, longitude, start, end)

    def _retrieve_point(self, latitude: float, longitude: float, start: date, end: date) -> list[dict[str, Any]]:
        try:
            import xarray as xr
        except ImportError as exc:
            raise RuntimeError("Falta instalar xarray y netCDF4 para leer los datos Copernicus") from exc

        request = {
            "product_type": ["reanalysis"],
            "variable": VARIABLES,
            "year": sorted({f"{d.year:04d}" for d in _days(start, end)}),
            "month": sorted({f"{d.month:02d}" for d in _days(start, end)}),
            "day": sorted({f"{d.day:02d}" for d in _days(start, end)}),
            "time": [f"{hour:02d}:00" for hour in range(24)],
            "data_format": "netcdf",
            "download_format": "unarchived",
            "area": [latitude + 0.1, longitude - 0.1, latitude - 0.1, longitude + 0.1],
        }
        with TemporaryDirectory(prefix="agroalerta-copernicus-") as temp_dir:
            target = Path(temp_dir) / "era5.nc"
            self._client().retrieve(DATASET, request, str(target))
            with xr.open_dataset(target) as dataset:
                point = dataset.sel(latitude=latitude, longitude=longitude, method="nearest")
                rows: list[dict[str, Any]] = []
                for timestamp in point["valid_time"].values:
                    timestamp_text = str(timestamp.astype("datetime64[s]"))
                    if not start.isoformat() <= timestamp_text[:10] <= end.isoformat():
                        continue
                    row: dict[str, Any] = {"timestamp": timestamp_text}
                    for variable in VARIABLES:
                        if variable in point:
                            value = point[variable].sel(valid_time=timestamp).item()
                            row[variable] = float(value) if value is not None else None
                    rows.append(row)
                return rows


def _days(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)
