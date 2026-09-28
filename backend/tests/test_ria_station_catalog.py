from app.connectors.ria_station_catalog import parse_ria_station_csv


def test_parses_official_ria_station_fields() -> None:
    content = """IDPROVINCIA;SPROVINCIA;IDESTACION;SESTACION;IDESTADO;VISIBLE;HUSO;XUTM;YUTM;SLATITUD;SLONGITUD;ALTITUD
41;Sevilla;123;La Campana;1;S;30;300000;4100000;37,123;-5,456;120
"""
    result = parse_ria_station_csv(content.encode("utf-8"))
    assert len(result) == 1
    assert result[0].station_code == "123"
    assert result[0].latitude == 37.123
    assert result[0].longitude == -5.456
    assert result[0].active is True


def test_ignores_station_without_coordinates() -> None:
    content = """IDESTACION;SESTACION;IDESTADO;SLATITUD;SLONGITUD
123;Sin coordenadas;1;;
"""
    assert parse_ria_station_csv(content.encode("utf-8")) == []
