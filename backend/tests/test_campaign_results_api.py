"""Pruebas de los endpoints de resultados de campaña.

Cubre el fallo real detectado el 2026-10-05: `create_campaign_result` no
persistía `yield_kg_ha`/`target_yield_*` y la lectura devolvía 500 con
`ValidationError: Field required`.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app, storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database() -> None:
    with storage._connect() as connection:
        connection.execute('DELETE FROM campaign_results')
        connection.execute('DELETE FROM campaign_decisions')
        connection.execute('DELETE FROM crop_campaigns')
        connection.execute('DELETE FROM agronomic_activities')
        connection.execute('DELETE FROM parcels')
    yield
    with storage._connect() as connection:
        connection.execute('DELETE FROM campaign_results')
        connection.execute('DELETE FROM campaign_decisions')
        connection.execute('DELETE FROM crop_campaigns')
        connection.execute('DELETE FROM agronomic_activities')
        connection.execute('DELETE FROM parcels')


def _campaign(headers: dict[str, str] | None = None) -> tuple[str, str]:
    parcel = client.post(
        '/api/v1/parcels',
        headers=headers or {},
        json={'label': 'Viñedo de resultados', 'latitude': 37.39, 'longitude': -5.99,
              'crop_type': 'vinedo', 'comarca': 'Campina de Sevilla'},
    )
    assert parcel.status_code == 201
    parcel_id = parcel.json()['id']
    campaign = client.post(
        f'/api/v1/parcels/{parcel_id}/campaigns',
        headers=headers or {},
        json={'parcel_id': parcel_id, 'crop_type': 'vinedo', 'disease_code': 'mildiu',
              'season_label': '2026/2027',
              'started_at': (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
              'status': 'active'},
    )
    assert campaign.status_code == 201
    return parcel_id, campaign.json()['id']


def test_campaign_result_is_created_listed_and_summarised() -> None:
    _, campaign_id = _campaign()

    created = client.post(f'/api/v1/campaigns/{campaign_id}/results', json={
        'campaign_id': campaign_id,
        'harvested_at': (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        'harvested_quantity_kg': 2500.0,
        'productive_area_ha': 1.25,
        'notes': 'Cosecha de prueba',
    })
    assert created.status_code == 201
    body = created.json()
    assert body['yield_kg_ha'] == 2000.0  # 2500 / 1.25

    listed = client.get(f'/api/v1/campaigns/{campaign_id}/results')
    assert listed.status_code == 200, listed.text
    results = listed.json()
    assert len(results) == 1
    assert results[0]['yield_kg_ha'] == 2000.0
    assert results[0]['harvested_quantity_kg'] == 2500.0

    summary = client.get(f'/api/v1/campaigns/{campaign_id}/results/summary')
    assert summary.status_code == 200, summary.text
    data = summary.json()
    assert data['result_count'] == 1
    assert data['harvested_quantity_kg'] == 2500.0
    assert data['yield_kg_ha'] == 2000.0


def test_campaign_results_of_other_owner_are_not_accessible() -> None:
    _, campaign_id = _campaign(headers={'Authorization': 'Bearer dueno-a'})
    client.post(
        f'/api/v1/campaigns/{campaign_id}/results',
        headers={'Authorization': 'Bearer dueno-a'},
        json={'campaign_id': campaign_id,
              'harvested_at': (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
              'harvested_quantity_kg': 1000.0,
              'productive_area_ha': 1.0},
    )

    assert client.get(
        f'/api/v1/campaigns/{campaign_id}/results',
        headers={'Authorization': 'Bearer dueno-b'},
    ).status_code == 404
    assert client.get(
        f'/api/v1/campaigns/{campaign_id}/results/summary',
        headers={'Authorization': 'Bearer dueno-b'},
    ).status_code == 404
