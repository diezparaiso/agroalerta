"""Consulta opcional de datos diarios SIAR del MAPA."""
import asyncio
import hashlib
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from app.connectors.siar_client import SiarClient
from app.core.async_cache import AsyncTTLCache
from app.core.security import optional_bearer_token

router = APIRouter(prefix="/api/v1/siar", tags=["SIAR/MAPA"])
_siar_cache = AsyncTTLCache(ttl_seconds=60 * 60, max_entries=256)
_siar_semaphore = asyncio.Semaphore(2)


@router.get("/daily")
async def get_daily_data(
    station: str = Query(min_length=1, max_length=120),
    start_date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    _token: str | None = Depends(optional_bearer_token),
) -> object:
    """Devuelve datos crudos si SIAR está configurado; si no, informa de ausencia."""
    if not station.strip():
        raise HTTPException(status_code=422, detail="station no puede estar vacío")
    client = SiarClient()
    cache_material = json.dumps([station.strip(), start_date, end_date, "siar-daily-v1"], separators=(",", ":"))
    cache_key = hashlib.sha256(cache_material.encode("utf-8")).hexdigest()
    try:
        async def retrieve():
            async with _siar_semaphore:
                return await client.get_daily_data(station, start_date, end_date)
        data = await _siar_cache.get_or_create(cache_key, retrieve)
        if data is None:
            raise HTTPException(
                status_code=503,
                detail="SIAR no está configurado; no se usarán datos SIAR para esta consulta",
            )
        return {"source": "SIAR-MAPA", "verified": False, "data": data}
    except HTTPException:
        raise
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="SIAR no devolvió JSON válido") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Tiempo de espera agotado al consultar SIAR") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail="SIAR devolvió un error HTTP") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="No se pudo obtener una respuesta JSON válida de SIAR") from exc
    finally:
        await client.aclose()
