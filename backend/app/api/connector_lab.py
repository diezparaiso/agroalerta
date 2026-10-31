"""Diagnóstico temporal y transparente de conectores externos."""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.connectors.aemet_client import AemetClient
from app.connectors.ria_ifapa_client import RiaIfapaClient
from app.core.config import settings

router = APIRouter(prefix="/api/v1/connector-lab", tags=["connector-lab"])


def _result(connector: str, status: str, configured: bool, data: Any = None, message: str | None = None, endpoint: str | None = None) -> dict[str, Any]:
    return {
        "connector": connector, "status": status, "configured": configured,
        "tested_at": datetime.now(timezone.utc).isoformat(), "endpoint": endpoint,
        "record_count": len(data) if isinstance(data, list) else (1 if data is not None else 0),
        "message": message, "raw_data": data,
    }


@router.get("/{connector}")
async def test_connector(connector: str, municipality_code: str = Query(default="41091", min_length=5, max_length=5)) -> dict[str, Any]:
    name = connector.lower().strip()
    if name == "ria":
        client = RiaIfapaClient()
        endpoint = f"{settings.ria_base_url}/estaciones"
        try:
            data = await client.list_stations()
            return _result("RIA-IFAPA", "connected" if data else "empty", True, data,
                           "Respuesta recibida desde el catálogo de estaciones RIA-IFAPA.", endpoint)
        except Exception as exc:
            return _result("RIA-IFAPA", "error", bool(settings.ria_base_url), None,
                           f"Consulta RIA-IFAPA fallida: {type(exc).__name__}.", endpoint)
        finally:
            await client.aclose()
    if name == "aemet":
        if not settings.aemet_api_key:
            return _result("AEMET", "not_configured", False, None, "Falta configurar AEMET_API_KEY en el backend.")
        client = AemetClient()
        endpoint = f"{settings.aemet_base_url}/prediccion/especifica/municipio/diaria/{municipality_code}"
        try:
            data = await client.get_daily_forecast(municipality_code)
            return _result("AEMET", "connected" if data else "empty", True, data,
                           f"Predicción diaria consultada para municipio INE {municipality_code}.", endpoint)
        except Exception as exc:
            return _result("AEMET", "error", True, None, f"Consulta AEMET fallida: {type(exc).__name__}.", endpoint)
        finally:
            await client.aclose()
    if name == "mapa":
        return _result("MAPA", "not_implemented", False, None, "Sin conector de consulta directa en esta integración.")
    if name == "sigpac":
        return _result("SIGPAC", "not_implemented", False, None, "Sin conector SIGPAC real en esta integración.")
    raise HTTPException(status_code=404, detail="Conector desconocido. Usa ria, aemet, mapa o sigpac.")
