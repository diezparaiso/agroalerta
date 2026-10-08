"""Pruebas de los endpoints de riego (eventos + inteligencia).

Cubre el fallo real detectado el 2026-10-05: la tabla `irrigation_events`
no se creaba en Storage y los endpoints respondían 500 en vivo.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app, storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database() -> None:
    with storage._connect() as connection:
        connection.execute('DELETE FROM irrigation_events')
        connection.execute('DELETE FROM parcels')
    yield
    with storage._connect() as connection:
        connection.execute('DELETE FROM irrigation_events')
        connection.execute('DELETE FROM parcels')


def _create_parcel(headers: dict[str, str] | None = None) -> str:
    response = client.post(
        '/api/v1/parcels',
        headers=headers or {},
        json={'label': 'Olivar con riego', 'latitude': 37.39, 'longitude': -5.99,
              'crop_type': 'olivar', 'comarca': 'Campina de Sevilla'},
    )
    assert response.status_code == 201
    return response.json()['id']


def _event_payload(parcel_id: str) -> dict:
    return {
        'parcel_id': parcel_id,
        'started_at': '2026-10-03T08:00:00+00:00',
        'duration_minutes': 90,
        'water_liters': 4200.0,
        'method': 'goteo',
        'notes': 'Riego de la mañana',
    }


def test_irrigation_event_is_created_and_listed() -> None:
    parcel_id = _create_parcel()

    created = client.post(f'/api/v1/parcels/{parcel_id}/irrigation/events', json=_event_payload(parcel_id))
    assert created.status_code == 201
    body = created.json()
    assert body['parcel_id'] == parcel_id
    assert body['water_liters'] == 4200.0
    assert body['owner_id'] == 'anonymous'

    listed = client.get(f'/api/v1/parcels/{parcel_id}/irrigation/events')
    assert listed.status_code == 200
    events = listed.json()
    assert len(events) == 1
    assert events[0]['method'] == 'goteo'
    assert events[0]['started_at'].startswith('2026-10-03')


def test_irrigation_intelligence_uses_persisted_events() -> None:
    parcel_id = _create_parcel()
    client.post(f'/api/v1/parcels/{parcel_id}/irrigation/events', json=_event_payload(parcel_id))

    response = client.get(f'/api/v1/parcels/{parcel_id}/irrigation/intelligence')

    assert response.status_code == 200
    body = response.json()
    assert body['parcel_id'] == parcel_id
    assert body['event_count'] == 1
    assert body['total_water_liters'] == 4200.0
    assert body['action'] in {'registrar', 'vigilar', 'revisar'}


def test_irrigation_requires_valid_payload() -> None:
    parcel_id = _create_parcel()
    payload = _event_payload(parcel_id)
    payload.pop('started_at')

    response = client.post(f'/api/v1/parcels/{parcel_id}/irrigation/events', json=payload)

    assert response.status_code == 422


def test_irrigation_events_of_other_owner_are_not_accessible() -> None:
    parcel_id = _create_parcel(headers={'Authorization': 'Bearer dueno-a'})
    client.post(
        f'/api/v1/parcels/{parcel_id}/irrigation/events',
        headers={'Authorization': 'Bearer dueno-a'},
        json=_event_payload(parcel_id),
    )

    assert client.get(
        f'/api/v1/parcels/{parcel_id}/irrigation/events',
        headers={'Authorization': 'Bearer dueno-b'},
    ).status_code == 404
    assert client.get(
        f'/api/v1/parcels/{parcel_id}/irrigation/intelligence',
        headers={'Authorization': 'Bearer dueno-b'},
    ).status_code == 404
