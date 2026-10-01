"""Endpoints de consulta diagnóstica para agregados RIA/IFAPA.

La respuesta se devuelve sin normalizar porque el esquema real del proveedor aún
debe verificarse. No usar estos datos directamente en el motor de riesgo.
"""
import asyncio
import hashlib
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.connectors.ria_ifapa_client import RiaIfapaClient
from app.core.async_cache import AsyncTTLCache
from app.core.security import optional_bearer_token

router = APIRouter(prefix="/api/v1/ria-ifapa", tags=["RIA/IFAPA"])
_daily_cache = AsyncTTLCache(ttl_seconds=60 * 60, max_entries=256)
_monthly_cache = AsyncTTLCache(ttl_seconds=24 * 60 * 60, max_entries=256)
_ria_semaphore = asyncio.Semaphore(3)


def _cache_key(kind: str, province: str, station: str, year: int, month_start: int, month_end: int) -> str:
    material = json.dumps([kind, province.strip(), station.strip(), year, month_start, month_end, "ria-ifapa-v1"], separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


async def _fetch_ria(kind: str, province: str, station: str, year: int, month_start: int, month_end: int) -> object:
    client = RiaIfapaClient()
    try:
        async with _ria_semaphore:
            if kind == "daily":
                return await client.get_daily_data(province, station, year, month_start, month_end)
            return await client.get_monthly_data(province, station, year, month_start, month_end)


@router.get("/daily")
async def get_daily_observations(
    province: str = Query(min_length=1, max_length=80),
    station: str = Query(min_length=1, max_length=120),
    year: int = Query(ge=1, le=9999),
    month_start: int = Query(ge=1, le=12),
    month_end: int = Query(ge=1, le=12),
    _token: str | None = Depends(optional_bearer_token),
) -> object:
    """Consulta agregados diarios crudos para verificar estaciones y esquema."""
    if not province.strip() or not station.strip():
        raise HTTPException(status_code=422, detail="province y station no pueden estar vacíos")
    if month_start > month_end:
        raise HTTPException(status_code=422, detail="month_start no puede superar month_end")

    try:
        return await _daily_cache.get_or_create(
            _cache_key("daily", province, station, year, month_start, month_end),
            lambda: _fetch_ria("daily", province, station, year, month_start, month_end),
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504, detail="Tiempo de espera agotado al consultar RIA/IFAPA"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502, detail="RIA/IFAPA devolvió un error HTTP"
        ) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(
            status_code=502, detail="No se pudo obtener una respuesta JSON válida de RIA/IFAPA"
        ) from exc


@router.get("/monthly")
async def get_monthly_observations(
    province: str = Query(min_length=1, max_length=80),
    station: str = Query(min_length=1, max_length=120),
    year: int = Query(ge=1, le=9999),
    month_start: int = Query(ge=1, le=12),
    month_end: int = Query(ge=1, le=12),
    _token: str | None = Depends(optional_bearer_token),
) -> object:
    """Consulta agregados mensuales crudos para verificar el contrato del proveedor."""
    if not province.strip() or not station.strip():
        raise HTTPException(status_code=422, detail="province y station no pueden estar vacíos")
    if month_start > month_end:
        raise HTTPException(status_code=422, detail="month_start no puede superar month_end")

    try:
        return await _monthly_cache.get_or_create(
            _cache_key("monthly", province, station, year, month_start, month_end),
            lambda: _fetch_ria("monthly", province, station, year, month_start, month_end),
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=504, detail="Tiempo de espera agotado al consultar RIA/IFAPA"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502, detail="RIA/IFAPA devolvió un error HTTP"
        ) from exc
    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(
            status_code=502, detail="No se pudo obtener una respuesta JSON válida de RIA/IFAPA"
        ) from exc
