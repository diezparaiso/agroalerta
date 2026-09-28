from app.domain.weather_station_selection import rank_weather_stations


def test_ranks_nearest_station_first() -> None:
    result = rank_weather_stations(
        37.3900,
        -5.9900,
        [
            {"source_code": "ria_ifapa", "station_code": "far", "latitude": 37.70, "longitude": -5.50, "observed_at": "2026-09-28"},
            {"source_code": "ria_ifapa", "station_code": "near", "latitude": 37.391, "longitude": -5.991, "observed_at": "2026-09-28"},
        ],
    )
    assert [item.station_code for item in result] == ["near", "far"]


def test_deduplicates_station_using_latest_observation() -> None:
    result = rank_weather_stations(
        37.3900,
        -5.9900,
        [
            {"source_code": "ria_ifapa", "station_code": "s1", "latitude": 37.40, "longitude": -5.99, "observed_at": "2026-09-27"},
            {"source_code": "ria_ifapa", "station_code": "s1", "latitude": 37.41, "longitude": -5.99, "observed_at": "2026-09-28"},
        ],
        max_stations=3,
    )
    assert len(result) == 1
    assert result[0].latitude == 37.41


def test_excludes_stations_outside_max_distance() -> None:
    result = rank_weather_stations(
        37.3900,
        -5.9900,
        [
            {"source_code": "ria_ifapa", "station_code": "far", "latitude": 38.30, "longitude": -5.99, "observed_at": "2026-09-28"},
        ],
        max_distance_km=20,
    )
    assert result == []
