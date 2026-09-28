from app.domain.geospatial import haversine_km


def test_haversine_zero() -> None:
    assert haversine_km(37.0, -5.0, 37.0, -5.0) == 0


def test_haversine_sevilla_cordoba_is_reasonable() -> None:
    distance = haversine_km(37.3891, -5.9845, 37.8882, -4.7794)
    assert 120 < distance < 150
