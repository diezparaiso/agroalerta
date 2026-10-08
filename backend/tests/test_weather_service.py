import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core import weather_service
from app.core.config import Settings
from app.core.weather_service import WeatherUnavailable, get_parcel_weather, parse_ria_coordinate
from app.main import app, storage
from app.schemas import Parcel

client = TestClient(app)

# Payloads con la forma real que devuelve RIA-IFAPA (verificado contra el servicio oficial).
_STATIONS_PAYLOAD = [
    {
        'provincia': {'id': 4, 'nombre': 'Almeria'},
        'codigoEstacion': '2',
        'nombre': 'Almeria',
        'bajoplastico': False,
        'activa': True,
        'visible': True,
        'longitud': '022408000W',
        'latitud': '365007000N',
        'altitud': 5,
    },
    {
        'provincia': {'id': 41, 'nombre': 'Sevilla'},
        'codigoEstacion': '12',
        'nombre': 'La Rinconada',
        'bajoplastico': False,
        'activa': True,
        'visible': True,
        'longitud': '055529000W',
        'latitud': '372724000N',
        'altitud': 25,
    },
    {
        'provincia': {'id': 41, 'nombre': 'Sevilla'},
        'codigoEstacion': '99',
        'nombre': 'Estacion inactiva junto a la parcela',
        'bajoplastico': False,
        'activa': False,
        'visible': True,
        'longitud': '055900000W',
        'latitud': '372400000N',
        'altitud': 10,
    },
    {
        'provincia': {'id': 41, 'nombre': 'Sevilla'},
        'codigoEstacion': '103',
        'nombre': 'Estacion bajo plastico junto a la parcela',
        'bajoplastico': True,
        'activa': True,
        'visible': True,
        'longitud': '055900000W',
        'latitud': '372400000N',
        'altitud': 10,
    },
]

_RECORDS_PAYLOAD = [
    {
        'fecha': '2026-09-29',
        'tempMedia': 24.27,
        'tempMax': 32.32,
        'tempMin': 16.26,
        'humedadMedia': 65.11,
        'humedadMax': 96.9,
        'humedadMin': 27.93,
        'precipitacion': 0.0,
    },
]


class _FakeRiaClient:
    daily_calls: list[tuple[str, str, date, date]] = []

    def __init__(self, client=None) -> None:
        pass

    async def list_stations(self) -> list:
        return _STATIONS_PAYLOAD

    async def get_daily_data(self, province: str, station: str, date_from: date, date_to: date) -> list:
        _FakeRiaClient.daily_calls.append((province, station, date_from, date_to))
        return _RECORDS_PAYLOAD

    async def aclose(self) -> None:
        pass


@pytest.fixture(autouse=True)
def clean_state():
    weather_service._weather_cache.clear()
    weather_service._stations_cache = None
    weather_service._aemet_cache.clear()
    _FakeRiaClient.daily_calls = []
    yield
    weather_service._weather_cache.clear()
    weather_service._stations_cache = None
    weather_service._aemet_cache.clear()
    with storage._connect() as connection:
        connection.execute('DELETE FROM parcels')


def _parcel() -> Parcel:
    now = datetime.now(timezone.utc)
    return Parcel(
        id='parcel-weather-1',
        owner_id='tester',
        created_at=now,
        updated_at=now,
        label='Olivar real',
        latitude=37.4,
        longitude=-5.99,
        crop_type='olivar',
        comarca='Campina de Sevilla',
    )


def _create_parcel() -> str:
    response = client.post(
        '/api/v1/parcels',
        json={'label': 'Olivar real', 'latitude': 37.4, 'longitude': -5.99, 'crop_type': 'olivar', 'comarca': 'Campina de Sevilla'},
    )
    assert response.status_code == 201
    return response.json()['id']


def test_parse_ria_coordinate() -> None:
    assert parse_ria_coordinate('372724000N') == pytest.approx(37.4567, abs=0.001)
    assert parse_ria_coordinate('055529000W') == pytest.approx(-5.9247, abs=0.001)
    assert parse_ria_coordinate('022408000W') == pytest.approx(-2.4022, abs=0.001)
    assert parse_ria_coordinate('no-es-coordenada') is None
    assert parse_ria_coordinate(None) is None


def test_get_parcel_weather_uses_nearest_active_station(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(weather_service, 'RiaIfapaClient', _FakeRiaClient)
    reading = asyncio.run(get_parcel_weather(_parcel()))

    assert reading['parcel_id'] == 'parcel-weather-1'
    assert reading['source'] == 'ria-ifapa'
    assert reading['temperature_c'] == 24.3
    assert reading['relative_humidity'] == 65.1
    assert reading['rainfall_mm_24h'] == 0.0
    assert reading['station_name'] == 'La Rinconada'
    assert 0 < reading['station_distance_km'] < 30
    assert reading['observed_at'] == datetime(2026, 9, 29, tzinfo=timezone.utc)

    assert len(_FakeRiaClient.daily_calls) == 1
    province, station, date_from, date_to = _FakeRiaClient.daily_calls[0]
    assert province == '41'
    assert station == '12'
    assert date_to == date.today()
    assert date_from == date.today() - timedelta(days=4)


def test_get_parcel_weather_raises_when_all_sources_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    async def failing_ria(latitude: float, longitude: float) -> dict:
        raise WeatherUnavailable('RIA-IFAPA inaccesible: timeout')

    async def failing_aemet(latitude: float, longitude: float) -> dict:
        raise WeatherUnavailable('AEMET_API_KEY no configurada')

    monkeypatch.setattr(weather_service, '_ria_weather', failing_ria)
    monkeypatch.setattr(weather_service, '_aemet_weather', failing_aemet)

    with pytest.raises(WeatherUnavailable) as error:
        asyncio.run(get_parcel_weather(_parcel()))
    message = str(error.value)
    assert 'RIA-IFAPA inaccesible: timeout' in message
    assert 'AEMET_API_KEY no configurada' in message


def test_parse_aemet_forecast_extracts_real_values() -> None:
    payload = [{
        'fecha': '2026-09-30',
        'temperatura': [{'valor': '25', 'periodo': '00-12'}, {'valor': '21', 'periodo': '12-24'}],
        'humedadRelativa': [{'valor': '70', 'periodo': '00-12'}, {'valor': '80', 'periodo': '12-24'}],
        'precipitacion': [{'valor': '0.2', 'periodo': '00-12'}, {'valor': '1.1', 'periodo': '12-24'}],
    }]
    reading = weather_service._parse_aemet_forecast(payload)
    assert reading is not None
    assert reading['source'] == 'aemet'
    assert reading['temperature_c'] == 23.0
    assert reading['relative_humidity'] == 75.0
    assert reading['rainfall_mm_24h'] == 1.3
    assert reading['station_distance_km'] is None
    assert reading['observed_at'] == datetime(2026, 9, 30, tzinfo=timezone.utc)


def test_parse_aemet_forecast_uses_max_min_when_series_absent() -> None:
    payload = {
        'fecha': '2026-09-30',
        'tempMaxima': {'valor': '30'},
        'tempMinima': {'valor': '20'},
        'humedadRelativa': [{'valor': '60'}],
    }
    reading = weather_service._parse_aemet_forecast(payload)
    assert reading is not None
    assert reading['temperature_c'] == 25.0


def test_parse_aemet_forecast_returns_none_without_usable_data() -> None:
    assert weather_service._parse_aemet_forecast([{'fecha': '2026-09-30'}]) is None
    assert weather_service._parse_aemet_forecast('respuesta inesperada') is None
    assert weather_service._parse_aemet_forecast(None) is None


def test_weather_endpoint_returns_real_ria_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(weather_service, 'RiaIfapaClient', _FakeRiaClient)
    monkeypatch.setattr(weather_service, 'settings', Settings(aemet_api_key=''))
    parcel_id = _create_parcel()

    response = client.get(f'/api/v1/weather/{parcel_id}')

    assert response.status_code == 200
    body = response.json()
    assert body['parcel_id'] == parcel_id
    assert body['source'] == 'ria-ifapa'
    assert body['temperature_c'] == 24.3
    assert body['station_name'] == 'La Rinconada'
    assert 'demo' not in str(body)


def test_weather_endpoint_returns_503_without_real_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    async def unavailable(parcel: Parcel) -> dict:
        raise WeatherUnavailable('Sin datos climaticos reales. RIA-IFAPA no responde | AEMET_API_KEY no configurada')

    monkeypatch.setattr('app.main.get_parcel_weather', unavailable)
    parcel_id = _create_parcel()

    response = client.get(f'/api/v1/weather/{parcel_id}')

    assert response.status_code == 503
    body = response.json()
    assert 'Sin datos climaticos reales' in body['detail']
    assert 'temperature_c' not in body


def test_parse_aemet_forecast_handles_real_aemet_structure() -> None:
    # Forma real del endpoint diario de AEMET, verificada en vivo el 2026-10-01:
    # lista con 'prediccion.dia' y variables como {'maxima', 'minima', 'dato'}.
    payload = [{
        'origen': {'productor': 'Agencia Estatal de Meteorologia - AEMET'},
        'prediccion': {
            'dia': [
                {
                    'fecha': '2026-09-30T00:00:00',
                    'temperatura': {'maxima': 33, 'minima': 19, 'dato': [{'value': 0, 'hora': 6}]},
                    'humedadRelativa': {'maxima': 90, 'minima': 40, 'dato': [{'value': 0, 'hora': 6}]},
                    'probPrecipitacion': {'maxima': 10, 'minima': 0},
                },
                {
                    'fecha': '2026-10-01T00:00:00',
                    'temperatura': {'maxima': 30, 'minima': 17},
                    'humedadRelativa': {'maxima': 80, 'minima': 30},
                },
            ],
        },
    }]

    reading = weather_service._parse_aemet_forecast(payload)

    assert reading is not None
    assert reading['source'] == 'aemet'
    assert reading['temperature_c'] == 26.0  # media de maxima 33 y minima 19
    assert reading['relative_humidity'] == 65.0  # media de maxima 90 y minima 40
    assert reading['rainfall_mm_24h'] is None  # el diario de AEMET no publica mm
    assert reading['observed_at'] == datetime(2026, 9, 30, tzinfo=timezone.utc)
    assert reading['station_name'] is None
    assert reading['station_distance_km'] is None
