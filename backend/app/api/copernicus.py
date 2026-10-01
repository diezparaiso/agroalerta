"""Endpoints para series puntuales de reanálisis Copernicus ERA5."""
import asyncio
import hashlib
import json

from fastapi import APIRouter, HTTPException, Query

from app.connectors.copernicus_client import CopernicusClient, CopernicusNotConfiguredError
from app.core.async_cache import AsyncTTLCache

router = APIRouter(prefix="/api/v1/copernicus", tags=["Copernicus CDS"])

# ERA5 requests are expensive; reuse identical successful results for six hours.
# Process-local only: multiple API workers have independent caches.
_era5_cache = AsyncTTLCache(ttl_seconds=6 * 60 * 60, max_entries=128)
_era5_semaphore = asyncio.Semaphore(2)


@router.get("/era5/hourly")
async def get_era5_hourly(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    start_date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    """Consulta ERA5; no incorpora estos valores al motor de riesgo automáticamente."""
    cache_material = json.dumps(
        [latitude, longitude, start_date, end_date, "reanalysis-era5-single-levels-v1"],
        separators=(",", ":"),
    )
    cache_key = hashlib.sha256(cache_material.encode("utf-8")).hexdigest()

    async def retrieve() -> list[dict]:
        async with _era5_semaphore:
            return await CopernicusClient().get_hourly_point(
                latitude, longitude, start_date, end_date
            )

    try:
        data = await _era5_cache.get_or_create(cache_key, retrieve)
        return {
            "source": "Copernicus Climate Data Store",
            "dataset": "reanalysis-era5-single-levels",
            "verified": False,
            "retrieval_completed": True,
            "cache_ttl_seconds": _era5_cache.ttl_seconds,
            "note": "ERA5 es un producto de reanálisis, no una observación local en tiempo real. La caché es temporal y local al proceso.",
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "units": {
                "2m_temperature": "K",
                "2m_dewpoint_temperature": "K",
                "total_precipitation": "m",
                "10m_u_component_of_wind": "m s-1",
                "10m_v_component_of_wind": "m s-1",
            },
            "data": data,
        }
    except CopernicusNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="No se pudo recuperar o procesar datos de Copernicus CDS") from exc
