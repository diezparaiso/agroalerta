"""Configurable SIGPAC WFS/OGC API connector.

The upstream service URL and layer are deployment configuration: SIGPAC endpoints and
layer names vary by publication. No demo geometries are ever returned as real data.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from app.core.security import optional_bearer_token

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


class ImportRequest(BaseModel):
    bbox: str = Field(description="Extensión WGS84: oeste,sur,este,norte")
    limit: int = Field(default=100, ge=1, le=1000)


def _database_path() -> Path:
    path = Path(os.getenv("AGROALERTA_DB_PATH", "backend/agroalerta.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sigpac_recintos (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                source_feature_id TEXT,
                properties_json TEXT NOT NULL,
                geometry_json TEXT,
                bbox_json TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                UNIQUE(owner_id, source_feature_id)
            )
        """)
        connection.commit()
    return path


def _owner(token: str | None) -> str:
    return token or "anonymous"


@router.post("/importar")
async def import_recintos(
    payload: ImportRequest,
    _token: str | None = Depends(optional_bearer_token),
) -> dict[str, Any]:
    """Fetch features from the configured provider and persist them for this user."""
    data = await search_recintos(bbox=payload.bbox, limit=payload.limit)
    owner_id = _owner(_token)
    path = _database_path()
    imported = 0
    updated = 0
    with sqlite3.connect(path) as connection:
        for feature in data["features"]:
            if not isinstance(feature, dict):
                continue
            feature_id = str(feature.get("id") or "")
            properties = feature.get("properties") or {}
            geometry = feature.get("geometry")
            if not isinstance(properties, dict):
                properties = {}
            if not feature_id:
                # Avoid accidental collisions when the provider omits stable feature IDs.
                feature_id = "derived:" + __import__("hashlib").sha256(
                    json.dumps([properties, geometry], sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest()
            existing = connection.execute(
                "SELECT id FROM sigpac_recintos WHERE owner_id = ? AND source_feature_id = ?",
                (owner_id, feature_id),
            ).fetchone()
            record_id = existing[0] if existing else str(uuid4())
            connection.execute("""
                INSERT INTO sigpac_recintos
                (id, owner_id, source_feature_id, properties_json, geometry_json, bbox_json, imported_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner_id, source_feature_id) DO UPDATE SET
                  properties_json=excluded.properties_json,
                  geometry_json=excluded.geometry_json,
                  bbox_json=excluded.bbox_json,
                  imported_at=excluded.imported_at
            """, (
                record_id, owner_id, feature_id,
                json.dumps(properties, ensure_ascii=False),
                json.dumps(geometry, ensure_ascii=False) if geometry is not None else None,
                json.dumps(data["bbox"]),
                datetime.now(timezone.utc).isoformat(),
            ))
            if existing:
                updated += 1
            else:
                imported += 1
        connection.commit()
    return {
        "source": "sigpac-wfs",
        "owner_id": owner_id,
        "received": data["numberReturned"],
        "imported": imported,
        "updated": updated,
        "note": "Los recintos se guardan por usuario; la geometría original se conserva en GeoJSON.",
    }


@router.get("/importados")
def list_imported_recintos(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    _token: str | None = Depends(optional_bearer_token),
) -> dict[str, Any]:
    owner_id = _owner(_token)
    path = _database_path()
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM sigpac_recintos WHERE owner_id = ? ORDER BY imported_at DESC LIMIT ? OFFSET ?",
            (owner_id, limit, offset),
        ).fetchall()
        total = connection.execute(
            "SELECT COUNT(*) FROM sigpac_recintos WHERE owner_id = ?", (owner_id,)
        ).fetchone()[0]
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "id": row["source_feature_id"],
            "geometry": json.loads(row["geometry_json"]) if row["geometry_json"] else None,
            "properties": json.loads(row["properties_json"]),
            "agroalerta": {
                "id": row["id"],
                "imported_at": row["imported_at"],
                "bbox": json.loads(row["bbox_json"]),
            },
        })
    return {"type": "FeatureCollection", "features": features, "total": total, "limit": limit, "offset": offset}
