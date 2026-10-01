"""Endpoints para series puntuales de reanálisis Copernicus ERA5."""
from fastapi import APIRouter, HTTPException, Query
from app.connectors.copernicus_client import CopernicusClient, CopernicusNotConfiguredError

router = APIRouter(prefix="/api/v1/copernicus", tags=["Copernicus CDS"])


@router.get("/era5/hourly")
async def get_era5_hourly(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    start_date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
) -> dict:
    """Consulta ERA5; no incorpora estos valores al motor de riesgo automáticamente."""
    client = CopernicusClient()
    try:
        data = await client.get_hourly_point(latitude, longitude, start_date, end_date)
        return {
            "source": "Copernicus Climate Data Store",
            "dataset": "reanalysis-era5-single-levels",
            "verified": True,
            "note": "ERA5 es un producto de reanálisis, no una observación local en tiempo real.",
            "coordinates": {"latitude": latitude, "longitude": longitude},
            "units": {
                "2m_temperature": "K",
                "2m_dewpoint_temperature": "K",
                "total_precipitation": "m",
                "10m_u_component_of_wind": "m s-1",
                "10m_v_component_of_wind": "m s-1",
            },
            "data": data,
        }
    except CopernicusNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="No se pudo recuperar o procesar datos de Copernicus CDS") from exc
