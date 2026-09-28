import asyncio
import logging
from datetime import datetime, timezone

from app.connectors.aemet_client import AemetClient
from app.connectors.ria_ifapa_client import RiaIfapaClient
from app.core.storage import Storage
from app.domain.weather_evidence import normalize_ria_daily

logger = logging.getLogger(__name__)


async def ingest_weather(
    municipality_code: str,
    province: str,
    station: str,
    year: int | None = None,
    month_start: int | None = None,
    month_end: int | None = None,
    station_latitude: float | None = None,
    station_longitude: float | None = None,
) -> dict[str, str]:
    """Ingresa RIA observada y consulta la prediccion AEMET.

    La observacion RIA se persiste cuando puede normalizarse. AEMET se
    mantiene como capa de prediccion y no se mezcla con observaciones.
    """
    now = datetime.now(timezone.utc)
    selected_year = year if year is not None else now.year
    selected_month_start = month_start if month_start is not None else now.month
    selected_month_end = month_end if month_end is not None else selected_month_start

    if not 1 <= selected_month_start <= 12:
        raise ValueError("month_start debe estar entre 1 y 12")
    if not 1 <= selected_month_end <= 12:
        raise ValueError("month_end debe estar entre 1 y 12")
    if selected_month_end < selected_month_start:
        raise ValueError("month_end no puede ser anterior a month_start")

    aemet = AemetClient()
    ria = RiaIfapaClient()
    storage = Storage()
    try:
        aemet_result, ria_result = await asyncio.gather(
            aemet.get_daily_forecast(municipality_code),
            ria.get_daily_data(
                province,
                station,
                selected_year,
                selected_month_start,
                selected_month_end,
            ),
        )

        evidence = normalize_ria_daily(ria_result, station=station)
        if evidence is not None and evidence.observed_at is not None:
            storage.save_weather_observation(
                source_code=evidence.source,
                station_code=station,
                observed_at=evidence.observed_at,
                latitude=station_latitude,
                longitude=station_longitude,
                temperature_c=evidence.temperature_c,
                relative_humidity=evidence.relative_humidity,
                rainfall_mm_24h=evidence.rainfall_mm_24h,
                confidence=evidence.confidence,
            )
            ria_status = "persisted"
        else:
            ria_status = "not-normalized"

        return {
            "status": "ingested",
            "ria": ria_status,
            "aemet": "forecast-fetched" if aemet_result is not None else "empty",
            "year": str(selected_year),
            "month_start": str(selected_month_start),
            "month_end": str(selected_month_end),
        }
    except Exception:
        logger.exception("Error ingiriendo datos agroclimaticos")
        return {"status": "stale-data"}
    finally:
        await aemet.client.aclose()
        await ria.client.aclose()
