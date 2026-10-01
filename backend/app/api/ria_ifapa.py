"""Endpoints de consulta diagnóstica para agregados RIA/IFAPA.

La respuesta se devuelve sin normalizar porque el esquema real del proveedor aún
debe verificarse. No usar estos datos directamente en el motor de riesgo.
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.connectors.ria_ifapa_client import RiaIfapaClient
from app.core.security import optional_bearer_token

router = APIRouter(prefix="/api/v1/ria-ifapa", tags=["RIA/IFAPA"])


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
    if month_start > month_end:
        raise HTTPException(status_code=422, detail="month_start no puede superar month_end")

    client = RiaIfapaClient()
    try:
        return await client.get_daily_data(
            province, station, year, month_start, month_end
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
    finally:
        await client.aclose()


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
    if month_start > month_end:
        raise HTTPException(status_code=422, detail="month_start no puede superar month_end")

    client = RiaIfapaClient()
    try:
        return await client.get_monthly_data(
            province, station, year, month_start, month_end
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
    finally:
        await client.aclose()
