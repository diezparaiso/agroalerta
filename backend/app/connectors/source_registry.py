"""Catalogo interno de fuentes agronomicas y geoespaciales.

La aplicacion no debe acoplar el motor de riesgo a una fuente concreta.
Cada fuente se normalizara a contratos internos antes de llegar al dominio.
"""

from typing import Final


DATA_SOURCES: Final[dict[str, dict[str, object]]] = {
    "raif_fitosanitario": {
        "name": "RAIF - seguimiento de plagas y enfermedades",
        "owner": "Junta de Andalucia / Servicio de Sanidad Vegetal",
        "coverage": "Andalucia",
        "granularity": "parcelas de seguimiento y muestreos",
        "cadence": "semanal en olivar; revisar por cultivo",
        "format": "ZIP/XML",
        "license": "CC BY 4.0",
        "status": "ready_for_ingestion",
        "role": "observaciones_fitopatologicas",
    },
    "raif_clima": {
        "name": "RAIF - red de estaciones agroclimaticas",
        "owner": "Junta de Andalucia / Servicio de Sanidad Vegetal",
        "coverage": "Andalucia",
        "granularity": "estacion",
        "cadence": "datos diarios; dataset publicado con frecuencia trimestral",
        "format": "ZIP/XML",
        "license": "CC BY 4.0",
        "status": "ready_for_ingestion",
        "role": "clima_agronomico",
    },
    "ria_ifapa": {
        "name": "RIA - Red de Informacion Agroclimatica de Andalucia",
        "owner": "IFAPA / Junta de Andalucia",
        "coverage": "Andalucia",
        "granularity": "estacion",
        "cadence": "consulta mediante API REST",
        "format": "REST/JSON",
        "license": "open_data",
        "status": "connector_exists_contract_validation_pending",
        "role": "clima_agronomico",
    },
    "aemet": {
        "name": "AEMET OpenData",
        "owner": "AEMET",
        "coverage": "Espana",
        "granularity": "municipio/estacion segun producto",
        "cadence": "actualizacion meteorologica operativa",
        "format": "REST/JSON",
        "license": "open_data",
        "status": "connector_exists_api_key_required",
        "role": "prediccion_y_observacion_meteorologica",
    },
    "ideandalucia": {
        "name": "IDEAndalucia / DERA / servicios OGC",
        "owner": "Junta de Andalucia",
        "coverage": "Andalucia",
        "granularity": "capas geograficas",
        "cadence": "segun capa",
        "format": "WMS/WFS",
        "license": "segun conjunto",
        "status": "integration_pending",
        "role": "contexto_geoespacial",
    },
    "sigpac": {
        "name": "SIGPAC",
        "owner": "FEGA + comunidades autonomas",
        "coverage": "Espana",
        "granularity": "recinto/parcela agricola",
        "cadence": "campana anual",
        "format": "geoespacial",
        "license": "public_administrative_data",
        "status": "integration_pending",
        "role": "identidad_geoespacial_de_parcela",
    },
    "mapa_fitosanitarios": {
        "name": "Registro oficial de productos fitosanitarios",
        "owner": "MAPA",
        "coverage": "Espana",
        "granularity": "producto/autorizacion",
        "cadence": "vigencia oficial",
        "format": "catalogo",
        "license": "official_public_information",
        "status": "catalog_import_exists_validation_pending",
        "role": "trazabilidad_de_producto",
    },
}


def list_data_sources() -> list[dict[str, object]]:
    """Devuelve una copia serializable del catalogo sin secretos."""
    return [
        {"code": code, **definition}
        for code, definition in DATA_SOURCES.items()
    ]
