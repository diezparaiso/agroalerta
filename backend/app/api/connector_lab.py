"""Diagnóstico temporal y transparente de conectores externos."""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.connectors.aemet_client import AemetClient
from app.connectors.ria_ifapa_client import RiaIfapaClient
from app.core.config import settings

router = APIRouter(prefix="/api/v1/connector-lab", tags=["connector-lab"])


def _result(connector: str, status: str, configured: bool, data: Any = None,
            message: str | None = None, endpoint: str | None = None) -> dict[str, Any]:
    return {
        "connector": connector,
        "status": status,
        "configured": configured,
        "tested_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "record_count": len(data) if isinstance(data, list) else (1 if data is not None else 0),
        "message": message,
        "raw_data": data,
    }


@router.get("/{connector}")
async def test_connector(
    connector: str,
    municipality_code: str = Query(default="41091", min_length=5, max_length=5),
) -> dict[str, Any]:
    """Ejecuta una consulta real y devuelve el JSON original sin normalizar."""
    name = connector.lower().strip()

    if name == "ria":
        client = RiaIfapaClient()
        try:
            data = await client.list_stations()
            if not isinstance(data, list):
                return _result("RIA-IFAPA", "invalid_response", True, data,
                               "La respuesta no tiene el formato de lista esperado.",
                               f"{settings.ria_base_url}/estaciones")
            return _result("RIA-IFAPA", "connected" if data else "empty", True, data,
                           "Respuesta recibida desde el servicio RIA-IFAPA.",
                           f"{settings.ria_base_url}/estaciones")
        except Exception as exc:
            return _result("RIA-IFAPA", "error", bool(settings.ria_base_url), None,
                           f"No se pudo consultar RIA-IFAPA: {type(exc).__name__}.",
                           f"{settings.ria_base_url}/estaciones")
        finally:
            await client.aclose()

    if name == "aemet":
        if not settings.aemet_api_key:
            return _result("AEMET", "not_configured", False, None,
                           "Falta configurar AEMET_API_KEY.")
        client = AemetClient()
        try:
            data = await client.get_daily_forecast(municipality_code)
            return _result("AEMET", "connected" if data else "empty", True, data,
                           f"Predicción diaria consultada para el municipio INE {municipality_code}.",
                           f"{settings.aemet_base_url}/prediccion/especifica/municipio/diaria/{municipality_code}")
        except Exception as exc:
            return _result("AEMET", "error", True, None,
                           f"No se pudo consultar AEMET: {type(exc).__name__}.")
        finally:
            await client.aclose()

    if name == "mapa":
        return _result("MAPA", "not_implemented", False, None,
                       "En esta rama existe importación de catálogo; no hay consulta directa conectada.")
    if name == "sigpac":
        return _result("SIGPAC", "not_implemented", False, None,
                       "No se ha encontrado un cliente SIGPAC real implementado en esta rama.")

    raise HTTPException(status_code=404, detail="Conector desconocido. Usa ria, aemet, mapa o sigpac.")
