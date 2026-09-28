from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class RiaStation:
    station_code: str
    name: str
    province: str | None
    latitude: float
    longitude: float
    altitude_m: float | None
    active: bool


class RiaStationCatalog:
    """Carga el catálogo oficial de estaciones RIA cuando se configura su CSV."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=20)

    async def fetch(self) -> list[RiaStation]:
        if not settings.ria_stations_url:
            raise RuntimeError("RIA_STATIONS_URL no configurada")
        response = await self.client.get(settings.ria_stations_url)
        response.raise_for_status()
        return parse_ria_station_csv(response.content)


def parse_ria_station_csv(content: bytes) -> list[RiaStation]:
    """Normaliza el CSV oficial usando latitud/longitud publicadas por la Junta."""
    text = content.decode("utf-8-sig")
    sample = text[:4096]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    stations: list[RiaStation] = []

    for row in reader:
        code = _text(row, "IDESTACION", "idEstacion", "codigo", "CODIGO")
        latitude = _number(row, "SLATITUD", "latitud", "LATITUD")
        longitude = _number(row, "SLONGITUD", "longitud", "LONGITUD")
        if not code or latitude is None or longitude is None:
            continue
        stations.append(
            RiaStation(
                station_code=code,
                name=_text(row, "SESTACION", "estacion", "ESTACION") or code,
                province=_text(row, "SPROVINCIA", "provincia", "PROVINCIA"),
                latitude=latitude,
                longitude=longitude,
                altitude_m=_number(row, "ALTITUD", "altitud"),
                active=_text(row, "IDESTADO", "estado", "ESTADO") in {"1", "true", "True", "S"},
            )
        )
    return stations


def _text(row: dict[str, Any], *names: str) -> str | None:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _number(row: dict[str, Any], *names: str) -> float | None:
    value = _text(row, *names)
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None
