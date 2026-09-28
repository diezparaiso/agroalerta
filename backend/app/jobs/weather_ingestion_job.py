import asyncio
import logging
from datetime import datetime, timezone

from app.connectors.aemet_client import AemetClient
from app.connectors.ria_ifapa_client import RiaIfapaClient

logger = logging.getLogger(__name__)


async def ingest_weather(
    municipality_code: str,
    province: str,
    station: str,
    year: int | None = None,
    month_start: int | None = None,
    month_end: int | None = None,
) -> dict[str, str]:
    """Ingresa prediccion AEMET y datos RIA para la ventana solicitada.

    Si el scheduler no proporciona una ventana, se consulta el mes UTC actual.
    Asi evitamos que la ingesta quede ligada a un año o periodo fijo.
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
    try:
        await asyncio.gather(
            aemet.get_daily_forecast(municipality_code),
            ria.get_daily_data(
                province,
                station,
                selected_year,
                selected_month_start,
                selected_month_end,
            ),
        )
        return {
            "status": "ingested",
            "year": str(selected_year),
            "month_start": str(selected_month_start),
            "month_end": str(selected_month_end),
        }
    except Exception:
        logger.exception("Error ingiriendo datos agroclimaticos")
        return {"status": "stale-data"}
