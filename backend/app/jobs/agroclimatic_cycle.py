from __future__ import annotations

import logging

from app.jobs.raif_ingestion_job import ingest_raif
from app.jobs.ria_station_catalog_job import sync_ria_station_catalog
from app.jobs.weather_refresh_job import refresh_all_parcel_weather

logger = logging.getLogger(__name__)


async def run_agroclimatic_cycle(owner_id: str | None = None) -> dict[str, object]:
    """Ejecuta el ciclo operativo en orden de dependencias.

    Orden:
    1. catálogo de estaciones RIA;
    2. evidencias RAIF;
    3. meteorología reciente por parcela;
    4. recalculado de riesgo y generación de alertas.

    Cada fuente externa falla de forma aislada para no convertir un fallo
    auxiliar en una falsa ausencia de datos de riesgo.
    """
    catalog = await sync_ria_station_catalog()

    raif_results: dict[str, object] = {}
    for crop in ("olivar", "vinedo"):
        try:
            raif_results[crop] = await ingest_raif(crop)
        except Exception:
            logger.exception("Error en ingesta RAIF para cultivo=%s", crop)
            raif_results[crop] = {"status": "error", "crop": crop}

    weather = await refresh_all_parcel_weather(owner_id)

    return {
        "status": "completed",
        "ria_station_catalog": catalog,
        "raif": raif_results,
        "weather_and_risk": weather,
    }


if __name__ == "__main__":
    import asyncio

    result = asyncio.run(run_agroclimatic_cycle())
    print(result)
