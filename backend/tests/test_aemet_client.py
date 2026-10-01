import httpx

from app.connectors.aemet_client import _load_json


def test_load_json_decodes_charset_declared_by_aemet() -> None:
    # AEMET declara charset=ISO-8859-15 y sus textos llevan acentos
    # (verificado en vivo el 2026-10-01); decodificar como UTF-8 fallaria.
    body = '[{"productor": "Meteorología - AEMET. Gobierno de España"}]'.encode('iso-8859-15')
    response = httpx.Response(
        200,
        content=body,
        headers={'content-type': 'application/json;charset=ISO-8859-15'},
    )

    payload = _load_json(response)

    assert payload[0]['productor'] == 'Meteorología - AEMET. Gobierno de España'
