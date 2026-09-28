from datetime import timezone

from app.connectors.raif_client import RaifClient


def test_parse_raif_xml_normalizes_sample_records() -> None:
    xml = b"""
    <ROOT>
      <MUESTREO>
        <PROVINCIA>SEVILLA</PROVINCIA>
        <MUNICIPIO>OSUNA</MUNICIPIO>
        <PARCELA>00014</PARCELA>
        <FECHA_MUESTREO>14/09/2026</FECHA_MUESTREO>
        <PLAGA>Repilo</PLAGA>
        <INCIDENCIA>12</INCIDENCIA>
      </MUESTREO>
    </ROOT>
    """
    records = RaifClient()._parse_xml(xml, "olivar", "RAIF_Olivar_Muestreos_2026.xml")

    assert records
    record = records[0]
    assert record.source_code == "raif_fitosanitario"
    assert record.province == "SEVILLA"
    assert record.municipality == "OSUNA"
    assert record.parcel == "00014"
    assert record.observed_at is not None
    assert record.observed_at.year == 2026
    assert record.observed_at.tzinfo == timezone.utc
    assert record.payload["fields"]["PLAGA"] == "Repilo"


def test_parse_raif_xml_supports_namespaces() -> None:
    xml = b"""
    <r:ROOT xmlns:r="urn:test">
      <r:MUESTREO>
        <r:PROVINCIA>CORDOBA</r:PROVINCIA>
        <r:MUNICIPIO>BAENA</r:MUNICIPIO>
        <r:PARCELA>12</r:PARCELA>
        <r:FECHA>2026-09-01</r:FECHA>
      </r:MUESTREO>
    </r:ROOT>
    """
    records = RaifClient()._parse_xml(xml, "olivar", "muestreos.xml")
    assert records[0].province == "CORDOBA"
    assert records[0].observed_at is not None
