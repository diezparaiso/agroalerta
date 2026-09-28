import pytest
from fastapi.testclient import TestClient

from app.main import app, storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database() -> None:
    with storage._connect() as connection:
        connection.execute('DELETE FROM risk_snapshots')
        connection.execute('DELETE FROM telemetry')
        connection.execute('DELETE FROM devices')
        connection.execute('DELETE FROM field_reports')
        connection.execute('DELETE FROM parcels')
        connection.execute('DELETE FROM push_tokens')


def test_health() -> None:
    assert client.get('/health').json()['status'] == 'ok'


def test_integrations_health_hides_credentials() -> None:
    response = client.get('/health/integrations')
    assert response.status_code == 200
    body = response.json()
    assert body['aemet']['mode'] in {'live', 'fallback'}
    assert 'api_key' not in str(body).lower()


def test_parcel_risk_flow() -> None:
    response = client.post('/api/v1/parcels', json={'label': 'Olivar de prueba', 'latitude': 37.39, 'longitude': -5.99, 'crop_type': 'olivar', 'comarca': 'Campina de Sevilla'})
    assert response.status_code == 201
    parcel_id = response.json()['id']
    risk = client.get(f'/api/v1/disease-risk/{parcel_id}')
    assert risk.status_code == 200
    assert risk.json()[0]['disease_code'] == 'repilo'


def test_parcels_are_isolated_by_bearer_token() -> None:
    first = client.post('/api/v1/parcels', headers={'Authorization': 'Bearer user-a'}, json={'label': 'Parcela A', 'latitude': 37.39, 'longitude': -5.99, 'crop_type': 'olivar', 'comarca': 'Sevilla'})
    second = client.post('/api/v1/parcels', headers={'Authorization': 'Bearer user-b'}, json={'label': 'Parcela B', 'latitude': 37.4, 'longitude': -5.9, 'crop_type': 'vinedo', 'comarca': 'Cordoba'})
    assert first.status_code == 201
    assert second.status_code == 201
    labels_a = [parcel['label'] for parcel in client.get('/api/v1/parcels', headers={'Authorization': 'Bearer user-a'}).json()]
    labels_b = [parcel['label'] for parcel in client.get('/api/v1/parcels', headers={'Authorization': 'Bearer user-b'}).json()]
    assert labels_a == ['Parcela A']
    assert labels_b == ['Parcela B']


def test_private_parcel_detail_and_telemetry_are_isolated() -> None:
    response = client.post('/api/v1/parcels', headers={'Authorization': 'Bearer owner-a'}, json={'label': 'Privada', 'latitude': 37.39, 'longitude': -5.99, 'crop_type': 'olivar', 'comarca': 'Sevilla'})
    parcel_id = response.json()['id']
    assert client.get(f'/api/v1/parcels/{parcel_id}', headers={'Authorization': 'Bearer owner-b'}).status_code == 404
    assert client.get(f'/api/v1/weather/{parcel_id}', headers={'Authorization': 'Bearer owner-b'}).status_code == 404
    assert client.get(f'/api/v1/telemetry/{parcel_id}', headers={'Authorization': 'Bearer owner-b'}).status_code == 404


def test_risk_history_deduplicates_repeated_calculations() -> None:
    response = client.post('/api/v1/parcels', json={'label': 'Historial', 'latitude': 37.39, 'longitude': -5.99, 'crop_type': 'olivar', 'comarca': 'Sevilla'})
    parcel_id = response.json()['id']
    client.get(f'/api/v1/disease-risk/{parcel_id}')
    client.get(f'/api/v1/disease-risk/{parcel_id}')
    history = client.get(f'/api/v1/risk-history/{parcel_id}').json()
    assert len(history) == 1


def test_risk_history_accepts_pagination_parameters() -> None:
    response = client.post('/api/v1/parcels', json={'label': 'Paginada', 'latitude': 37.39, 'longitude': -5.99, 'crop_type': 'olivar', 'comarca': 'Sevilla'})
    parcel_id = response.json()['id']
    history = client.get(f'/api/v1/risk-history/{parcel_id}?limit=1&offset=0')
    assert history.status_code == 200
    assert len(history.json()) <= 1


def test_production_requires_firebase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.delenv('FIREBASE_SERVICE_ACCOUNT_JSON', raising=False)
    assert client.get('/api/v1/parcels').status_code == 401
    assert client.get('/api/v1/parcels', headers={'Authorization': 'Bearer dev-token'}).status_code == 503
    monkeypatch.setenv('ENVIRONMENT', 'development')


def test_risk_uses_registered_sensor_telemetry() -> None:
    parcel = client.post(
        '/api/v1/parcels',
        headers={'Authorization': 'Bearer agronomo'},
        json={'label': 'Olivar monitorizado', 'latitude': 37.39, 'longitude': -5.99, 'crop_type': 'olivar', 'comarca': 'Sevilla'},
    )
    assert parcel.status_code == 201
    parcel_id = parcel.json()['id']

    device = client.post(
        '/api/v1/devices',
        headers={'Authorization': 'Bearer agronomo'},
        json={'parcel_id': parcel_id, 'device_id': 'sensor-01', 'name': 'Estacion parcela', 'device_type': 'weather_station'},
    )
    assert device.status_code == 201

    telemetry = client.post(
        '/api/v1/telemetry',
        headers={'Authorization': 'Bearer agronomo'},
        json={
            'parcel_id': parcel_id,
            'device_id': 'sensor-01',
            'temperature_c': 20,
            'relative_humidity': 95,
            'leaf_wetness_hours': 16,
            'soil_moisture': 75,
            'rainfall_mm_24h': 20,
            'battery_percent': 88,
            'measured_at': '2026-09-28T10:00:00+00:00',
        },
    )
    assert telemetry.status_code == 202

    risk = client.get(f'/api/v1/disease-risk/{parcel_id}', headers={'Authorization': 'Bearer agronomo'})
    assert risk.status_code == 200
    body = risk.json()[0]
    assert body['confidence_level'] == 'alta'
    variables = {item['name']: item['value'] for item in body['variables_used']}
    assert variables['lluvia_24h_mm'] == 20
    assert variables['humedad_relativa'] == 95
