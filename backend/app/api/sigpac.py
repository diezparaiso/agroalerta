"""Configurable SIGPAC WFS/OGC API connector.

The upstream service URL and layer are deployment configuration: SIGPAC endpoints and
layer names vary by publication. No demo geometries are ever returned as real data.
"""
import os
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/sigpac", tags=["SIGPAC"])


def _settings() -> tuple[str, str]:
    url = os.getenv("SIGPAC_WFS_URL", "").strip()
    layer = os.getenv("SIGPAC_WFS_TYPENAME", "").strip()
    if not url or not layer:
        raise HTTPException(
            status_code=503,
            detail="SIGPAC no configurado: defina SIGPAC_WFS_URL y SIGPAC_WFS_TYPENAME con el servicio oficial validado.",
        )
    if not url.startswith(("https://", "http://")):
        raise HTTPException(status_code=503, detail="SIGPAC_WFS_URL debe ser una URL HTTP(S).")
    return url, layer


@router.get("/health")
async def sigpac_health() -> dict[str, Any]:
    url = os.getenv("SIGPAC_WFS_URL", "").strip()
    layer = os.getenv("SIGPAC_WFS_TYPENAME", "").strip()
    return {
        "configured": bool(url and layer),
        "mode": "live" if url and layer else "disabled",
        "service_url_configured": bool(url),
        "layer_configured": bool(layer),
        "note": "La configuración no garantiza disponibilidad; use /recintos para verificar el servicio.",
    }


@router.get("/recintos")
async def search_recintos(
    bbox: str = Query(..., description="Extensión WGS84: oeste,sur,este,norte"),
    limit: int = Query(100, ge=1, le=1000),
) -> dict[str, Any]:
    """Fetch real recinto features from a configured WFS, returning GeoJSON."""
    url, layer = _settings()
    try:
        coords = [float(part.strip()) for part in bbox.split(",")]
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="bbox debe contener cuatro coordenadas numéricas.")
    if len(coords) != 4:
        raise HTTPException(status_code=422, detail="bbox debe tener formato oeste,sur,este,norte.")
    west, south, east, north = coords
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise HTTPException(status_code=422, detail="bbox no válida.")
    params = {
        "service": "WFS",
        "version": os.getenv("SIGPAC_WFS_VERSION", "2.0.0"),
        "request": "GetFeature",
        "typeNames": layer,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
        "bbox": f"{west},{south},{east},{north},EPSG:4326",
        "count": limit,
    }
    timeout = httpx.Timeout(20.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="El servicio SIGPAC ha agotado el tiempo de espera.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="No se pudo consultar SIGPAC o la respuesta no es GeoJSON válido.") from exc
    if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise HTTPException(status_code=502, detail="SIGPAC no devolvió una FeatureCollection GeoJSON válida.")
    return {
        "type": "FeatureCollection",
        "features": payload["features"],
        "numberReturned": len(payload["features"]),
        "source": "sigpac-wfs",
        "bbox": coords,
        "truncated": len(payload["features"]) >= limit,
    }
