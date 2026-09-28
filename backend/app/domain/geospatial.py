from math import atan2, cos, radians, sin, sqrt


EARTH_RADIUS_KM = 6371.0088


def haversine_km(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """Distancia geodesica aproximada entre dos coordenadas WGS84."""
    lat1, lat2 = radians(latitude_1), radians(latitude_2)
    dlat = lat2 - lat1
    dlon = radians(longitude_2 - longitude_1)
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * atan2(sqrt(a), sqrt(1 - a))
