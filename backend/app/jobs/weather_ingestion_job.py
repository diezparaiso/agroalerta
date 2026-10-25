import asyncio
import logging
from datetime import date, timedelta

from app.connectors.aemet_client import AemetClient
from app.connectors.ria_ifapa_client import RiaIfapaClient

logger = logging.getLogger(__name__)


async def ingest_weather(municipality_code: str, province: str, station: str) -> dict[str, str]:
    """Punto de entrada para un scheduler externo (Celery, cron o Cloud Run Jobs)."""
    aemet = AemetClient()
    ria = RiaIfapaClient()
    today = date.today()
    try:
        await asyncio.gather(
            aemet.get_daily_forecast(municipality_code),
            ria.get_daily_data(province, station, today - timedelta(days=7), today),
        )
        return {'status': 'ingested'}
    except Exception:
        logger.exception('Error ingiriendo datos agroclimaticos')
        return {'status': 'stale-data'}
    finally:
        await aemet.aclose()
        await ria.aclose()
