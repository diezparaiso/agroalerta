from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.connectors.ria_station_catalog import RiaStationCatalog
from app.core.storage import Storage

logger = logging.getLogger(__name__)


async def sync_ria_station_catalog() -> dict[str, int | str]:
    """Sincroniza el catálogo oficial de estaciones RIA con la BD local."""
    catalog = RiaStationCatalog()
    storage = Storage()
    try:
        stations = await catalog.fetch()
        for station in stations:
            storage.save_weather_station(
                source_code="ria_ifapa",
                station_code=station.station_code,
                name=station.name,
                province=station.province,
                latitude=station.latitude,
                longitude=station.longitude,
                altitude_m=station.altitude_m,
                active=station.active,
            )
        active_count = sum(1 for station in stations if station.active)
        return {
            "status": "synced",
            "stations": len(stations),
            "active": active_count,
        }
    except Exception:
        logger.exception("Error sincronizando catálogo de estaciones RIA")
        return {"status": "stale-data", "stations": 0, "active": 0}
    finally:
        await catalog.client.aclose()
