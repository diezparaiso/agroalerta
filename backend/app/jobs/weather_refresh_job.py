from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.core.storage import Storage
from app.jobs.weather_ingestion_job import ingest_weather_for_parcel

logger = logging.getLogger(__name__)


async def refresh_all_parcel_weather() -> dict[str, int | str]:
    """Actualiza RIA para todas las parcelas almacenadas.

    Es idempotente a nivel de observación: SQLite reemplaza la misma
    combinación estación/fecha si vuelve a recibirse.
    """
    storage = Storage()
    parcels = storage.list_parcels()
    updated = 0
    failed = 0

    for parcel in parcels:
        try:
            result = await ingest_weather_for_parcel(
                parcel.latitude,
                parcel.longitude,
            )
            if result.get("status") == "ingested":
                updated += 1
            else:
                failed += 1
        except Exception:
            failed += 1
            logger.exception("Error actualizando meteorología de parcela %s", parcel.id)

    return {
        "status": "completed",
        "parcels": len(parcels),
        "updated": updated,
        "failed": failed,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
