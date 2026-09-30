"""Clima real para AgroAlerta: RIA-IFAPA y AEMET OpenData.

El endpoint /api/v1/weather/{parcel_id} consulta las fuentes en este orden:

1. RIA-IFAPA: estacion agroclimatica activa mas cercana a la parcela, sin
   clave API. Endpoints oficiales verificados:
   GET /estaciones y GET /datosdiarios/forceEt0/{provincia}/{estacion}/{desde}/{hasta}.
2. AEMET OpenData: prediccion diaria del municipio de referencia, solo si
   AEMET_API_KEY esta configurada; la parcela se resuelve a la capital
   andaluza mas cercana (aproximacion documentada por coordenadas).

Si ninguna fuente devuelve datos reales se lanza WeatherUnavailable y el
endpoint contesta 503: este modulo nunca devuelve valores ficticios.
"""

import logging
import math
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.connectors.aemet_client import AemetClient
from app.connectors.ria_ifapa_client import RiaIfapaClient
from app.core.config import settings
from app.schemas import Parcel

logger = logging.getLogger(__name__)

_STATIONS_TTL_SECONDS = 24 * 3600.0
_WEATHER_TTL_SECONDS = 10 * 60.0
_RIA_HISTORY_DAYS = 4
_MAX_CACHED_LOCATIONS = 256

_stations_cache: tuple[float, list[Any]] | None = None
_weather_cache: dict[str, tuple[float, dict[str, Any]]] = {}

# Codigos INE de las capitales andaluzas: con AEMET la parcela se resuelve
# al municipio de la capital mas cercana (aproximacion por coordenadas).
_ANDALUSIAN_CAPITALS: tuple[tuple[str, float, float, str], ...] = (
    ('Almeria', 36.8341, -2.4634, '04013'),
    ('Cadiz', 36.5297, -6.2886, '11012'),
    ('Cordoba', 37.8882, -4.7794, '14021'),
    ('Granada', 37.1773, -3.5986, '18087'),
    ('Huelva', 37.2614, -6.9447, '21041'),
    ('Jaen', 37.7796, -3.7849, '23050'),
    ('Malaga', 36.7194, -4.4217, '29067'),
    ('Sevilla', 37.3891, -5.9845, '41091'),
)


class WeatherUnavailable(Exception):
    """Ninguna fuente externa ha podido devolver datos climaticos reales."""


def parse_ria_coordinate(value: str | None) -> float | None:
    """Convierte una coordenada RIA ('375951000N') a grados decimales."""
    if not value or len(value) != 10:
        return None
    hemisphere = value[-1].upper()
    digits = value[:-1]
    if hemisphere not in {'N', 'S', 'E', 'W'} or not digits.isdigit():
        return None
    degrees = int(digits[0:2])
    minutes = int(digits[2:4])
    seconds = int(digits[4:6])
    thousandths = int(digits[6:9])
    decimal = degrees + minutes / 60 + (seconds + thousandths / 1000) / 3600
    return -decimal if hemisphere in {'S', 'W'} else decimal


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _as_float(value: Any) -> float | None:
    if isinstance(value, dict):
        value = value.get('valor')
    if isinstance(value, str):
        value = value.strip().replace(',', '.')
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _values_of(items: Any) -> list[float]:
    raw_items = items if isinstance(items, list) else [items]
    values = [_as_float(item) for item in raw_items]
    return [value for value in values if value is not None]


def _parse_observed_date(value: Any) -> datetime:
    if isinstance(value, str) and len(value) >= 10:
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


async def _nearest_ria_station(client: RiaIfapaClient, latitude: float, longitude: float) -> tuple[dict[str, Any], float]:
    """Estacion activa mas cercana a la parcela y distancia en km."""
    global _stations_cache
    now = time.monotonic()
    if _stations_cache is None or now - _stations_cache[0] > _STATIONS_TTL_SECONDS:
        payload = await client.list_stations()
        stations = payload if isinstance(payload, list) else []
        _stations_cache = (now, stations)
    candidates: list[tuple[float, dict[str, Any]]] = []
    for station in _stations_cache[1]:
        if not isinstance(station, dict) or not station.get('activa') or station.get('bajoplastico'):
            continue
        station_lat = parse_ria_coordinate(station.get('latitud'))
        station_lon = parse_ria_coordinate(station.get('longitud'))
        if station_lat is None or station_lon is None:
            continue
        distance = _haversine_km(latitude, longitude, station_lat, station_lon)
        candidates.append((distance, station))
    if not candidates:
        raise WeatherUnavailable('RIA-IFAPA no tiene estaciones activas con coordenadas validas')
    distance_km, station = min(candidates, key=lambda candidate: candidate[0])
    return station, distance_km


def _build_ria_reading(records: Any, station: dict[str, Any], distance_km: float) -> dict[str, Any]:
    latest: tuple[dict[str, Any], float, float] | None = None
    for record in records:
        if not isinstance(record, dict):
            continue
        temperature = _as_float(record.get('tempMedia'))
        humidity = _as_float(record.get('humedadMedia'))
        if temperature is not None and humidity is not None:
            latest = (record, temperature, humidity)
    if latest is None:
        raise WeatherUnavailable('RIA-IFAPA: los registros diarios no incluyen temperatura y humedad')
    record, temperature, humidity = latest
    precipitation = _as_float(record.get('precipitacion'))
    station_name = str(station.get('nombre') or station.get('codigoEstacion') or 'estacion RIA')
    return {
        'temperature_c': round(temperature, 1),
        'relative_humidity': round(humidity, 1),
        'rainfall_mm_24h': round(precipitation, 1) if precipitation is not None else 0.0,
        'station_distance_km': round(distance_km, 1),
        'observed_at': _parse_observed_date(record.get('fecha')),
        'station_name': station_name,
        'source': 'ria-ifapa',
    }


async def _ria_weather(latitude: float, longitude: float) -> dict[str, Any]:
    client = RiaIfapaClient()
    try:
        station, distance_km = await _nearest_ria_station(client, latitude, longitude)
        province = station.get('provincia') or {}
        province_id = province.get('id') if isinstance(province, dict) else None
        station_code = station.get('codigoEstacion')
        if province_id is None or not station_code:
            raise WeatherUnavailable('RIA-IFAPA: la estacion mas cercana no tiene provincia o codigo validos')
        today = date.today()
        records = await client.get_daily_data(
            str(province_id),
            str(station_code),
            today - timedelta(days=_RIA_HISTORY_DAYS),
            today,
        )
    except WeatherUnavailable:
        raise
    except Exception as exc:
        raise WeatherUnavailable(f'RIA-IFAPA inaccesible: {exc}') from exc
    finally:
        await client.aclose()
    if not isinstance(records, list) or not records:
        raise WeatherUnavailable('RIA-IFAPA: sin registros diarios recientes para la estacion seleccionada')
    return _build_ria_reading(records, station, distance_km)


def _nearest_capital(latitude: float, longitude: float) -> tuple[str, str]:
    """(codigo INE, nombre) de la capital andaluza mas cercana a la parcela."""
    name, _lat, _lon, ine = min(
        _ANDALUSIAN_CAPITALS,
        key=lambda capital: _haversine_km(latitude, longitude, capital[1], capital[2]),
    )
    return ine, name


def _parse_aemet_forecast(payload: Any) -> dict[str, Any] | None:
    """Extrae la prediccion del primer dia del formato diario de AEMET."""
    if isinstance(payload, list):
        day = next((item for item in payload if isinstance(item, dict)), None)
    elif isinstance(payload, dict):
        day = payload
    else:
        day = None
    if day is None:
        return None
    temperatures = _values_of(day.get('temperatura'))
    if not temperatures:
        tmax = _as_float(day.get('tempMaxima'))
        tmin = _as_float(day.get('tempMinima'))
        if tmax is not None and tmin is not None:
            temperatures = [(tmax + tmin) / 2]
    humidities = _values_of(day.get('humedadRelativa'))
    if not temperatures or not humidities:
        return None
    rainfalls = _values_of(day.get('precipitacion'))
    return {
        'temperature_c': round(sum(temperatures) / len(temperatures), 1),
        'relative_humidity': round(sum(humidities) / len(humidities), 1),
        'rainfall_mm_24h': round(sum(rainfalls), 1) if rainfalls else None,
        'station_distance_km': None,
        'observed_at': _parse_observed_date(day.get('fecha')),
        'station_name': None,
        'source': 'aemet',
    }


async def _aemet_weather(latitude: float, longitude: float) -> dict[str, Any]:
    if not settings.aemet_api_key:
        raise WeatherUnavailable('AEMET_API_KEY no configurada')
    municipality, capital = _nearest_capital(latitude, longitude)
    client = AemetClient()
    try:
        payload = await client.get_daily_forecast(municipality)
    except Exception as exc:
        raise WeatherUnavailable(f'AEMET inaccesible para {capital}: {exc}') from exc
    finally:
        await client.aclose()
    reading = _parse_aemet_forecast(payload)
    if reading is None:
        raise WeatherUnavailable(f'AEMET devolvio un formato sin datos utilizables para {capital}')
    return reading


async def get_parcel_weather(parcel: Parcel) -> dict[str, Any]:
    """Lectura climatica real para la parcela; lanza WeatherUnavailable si no hay datos."""
    location = f'{round(parcel.latitude, 3)}:{round(parcel.longitude, 3)}'
    now = time.monotonic()
    cached = _weather_cache.get(location)
    if cached is not None and now - cached[0] <= _WEATHER_TTL_SECONDS:
        return {'parcel_id': parcel.id, **cached[1]}

    failures: list[str] = []
    for source in (_ria_weather, _aemet_weather):
        try:
            reading = await source(parcel.latitude, parcel.longitude)
        except WeatherUnavailable as exc:
            failures.append(str(exc))
            continue
        if len(_weather_cache) >= _MAX_CACHED_LOCATIONS:
            _weather_cache.clear()
        _weather_cache[location] = (now, reading)
        return {'parcel_id': parcel.id, **reading}
    raise WeatherUnavailable('Sin datos climaticos reales. ' + ' | '.join(failures))
