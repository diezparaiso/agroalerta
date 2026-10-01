"""SIGPAC HubCloud OGC API Features connector and SQLite import."""
import hashlib
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
DEFAULT_OGC_URL = "https://sigpac-hubcloud.es/ogcapi"
DEFAULT_COLLECTION = "recintos"


def _settings() -> tuple[str, str]:
    base_url = os.getenv("SIGPAC_OGC_API_URL", DEFAULT_OGC_URL).strip().rstrip("/")
    collection = os.getenv("SIGPAC_OGC_COLLECTION", DEFAULT_COLLECTION).strip()
    if not base_url.startswith(("https://", "http://")) or not collection:
        raise HTTPException(status_code=503, detail="Configuración SIGPAC inválida.")
    return base_url, collection


def _validate_bbox(bbox: str) -> list[float]:
    try:
        coords = [float(part.strip()) for part in bbox.split(",")]
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="bbox debe contener cuatro coordenadas numéricas.")
    if len(coords) != 4:
        raise HTTPException(status_code=422, detail="bbox debe tener formato oeste,sur,este,norte.")
    west, south, east, north = coords
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise HTTPException(status_code=422, detail="bbox no válida.")
    return coords


async def _get_geojson_items(bbox: str, limit: int) -> dict[str, Any]:
    base_url, collection = _settings()
    coords = _validate_bbox(bbox)
    url = f"{base_url}/collections/{collection}/items"
    params = {"f": "json", "bbox": ",".join(map(str, coords)), "limit": limit}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=8.0), follow_redirects=True) as client:
            response = await client.get(url, params=params, headers={"Accept": "application/geo+json, application/json"})
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="SIGPAC HubCloud agotó el tiempo de espera.") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"SIGPAC HubCloud respondió HTTP {exc.response.status_code}.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="No se pudo consultar SIGPAC HubCloud o la respuesta no es JSON válido.") from exc
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
        raise HTTPException(status_code=502, detail="SIGPAC HubCloud no devolvió una FeatureCollection GeoJSON válida.")
    return {
        "type": "FeatureCollection",
        "features": data["features"],
        "numberReturned": len(data["features"]),
        "source": "sigpac-hubcloud-ogcapi",
        "collection": collection,
        "bbox": coords,
        "truncated": len(data["features"]) >= limit,
        "links": data.get("links", []),
    }


@router.get("/health")
async def sigpac_health() -> dict[str, Any]:
    base_url, collection = _settings()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=4.0), follow_redirects=True) as client:
            response = await client.get(f"{base_url}/collections/{collection}?f=json")
            response.raise_for_status()
            metadata = response.json()
        return {
            "configured": True,
            "reachable": isinstance(metadata, dict) and metadata.get("id") == collection,
            "provider": "SIGPAC HubCloud",
            "base_url": base_url,
            "collection": collection,
        }
    except (httpx.HTTPError, ValueError):
        return {
            "configured": True,
            "reachable": False,
            "provider": "SIGPAC HubCloud",
            "base_url": base_url,
            "collection": collection,
        }


@router.get("/recintos")
async def search_recintos(
    bbox: str = Query(..., description="Extensión geográfica: oeste,sur,este,norte"),
    limit: int = Query(100, ge=1, le=1000),
) -> dict[str, Any]:
    """Return live SIGPAC recinto features from the HubCloud OGC API."""
    return await _get_geojson_items(bbox, limit)


class ImportRequest(BaseModel):
    bbox: str = Field(description="Extensión geográfica: oeste,sur,este,norte")
    limit: int = Field(default=100, ge=1, le=1000)
    feature_ids: list[str] | None = Field(default=None, min_length=1, max_length=100)


def _database_path() -> Path:
    path = Path(os.getenv("AGROALERTA_DB_PATH", "backend/agroalerta.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sigpac_recintos (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                source_feature_id TEXT NOT NULL,
                properties_json TEXT NOT NULL,
                geometry_json TEXT,
                bbox_json TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                UNIQUE(owner_id, source_feature_id)
            )
        """)
        connection.commit()
    return path


def _stable_feature_id(feature: dict[str, Any]) -> str:
    if feature.get("id") is not None:
        return str(feature["id"])
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry")
    return "derived:" + hashlib.sha256(
        json.dumps([properties, geometry], sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@router.post("/importar")
async def import_recintos(
    payload: ImportRequest,
    _token: str | None = Depends(optional_bearer_token),
) -> dict[str, Any]:
    data = await search_recintos(bbox=payload.bbox, limit=payload.limit)
    owner_id = _token or "anonymous"
    selected_ids = set(payload.feature_ids or [])
    features = data["features"]
    if selected_ids:
        features = [feature for feature in features if isinstance(feature, dict) and _stable_feature_id(feature) in selected_ids]
        missing_ids = selected_ids - {_stable_feature_id(feature) for feature in features}
        if missing_ids:
            raise HTTPException(status_code=422, detail="Uno o más recintos seleccionados no están presentes en los resultados del área consultada.")
    path = _database_path()
    imported = updated = 0
    with sqlite3.connect(path) as connection:
        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties") or {}
            if not isinstance(properties, dict):
                properties = {}
            feature_id = _stable_feature_id(feature)
            existing = connection.execute(
                "SELECT id FROM sigpac_recintos WHERE owner_id=? AND source_feature_id=?",
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
                json.dumps(feature.get("geometry"), ensure_ascii=False) if feature.get("geometry") is not None else None,
                json.dumps(data["bbox"]),
                datetime.now(timezone.utc).isoformat(),
            ))
            if existing:
                updated += 1
            else:
                imported += 1
        connection.commit()
    return {
        "source": data["source"], "owner_id": owner_id, "received": data["numberReturned"],
        "imported": imported, "updated": updated,
        "note": "Se conservan geometrías y atributos originales; los identificadores repetidos se actualizan.",
    }


@router.get("/importados")
def list_imported_recintos(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    _token: str | None = Depends(optional_bearer_token),
) -> dict[str, Any]:
    owner_id = _token or "anonymous"
    path = _database_path()
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM sigpac_recintos WHERE owner_id=? ORDER BY imported_at DESC LIMIT ? OFFSET ?",
            (owner_id, limit, offset),
        ).fetchall()
        total = connection.execute("SELECT COUNT(*) FROM sigpac_recintos WHERE owner_id=?", (owner_id,)).fetchone()[0]
    features = [{
        "type": "Feature",
        "id": row["source_feature_id"],
        "geometry": json.loads(row["geometry_json"]) if row["geometry_json"] else None,
        "properties": json.loads(row["properties_json"]),
        "agroalerta": {"id": row["id"], "imported_at": row["imported_at"], "bbox": json.loads(row["bbox_json"])},
    } for row in rows]
    return {"type": "FeatureCollection", "features": features, "total": total, "limit": limit, "offset": offset}
