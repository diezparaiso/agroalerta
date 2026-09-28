import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    aemet_base_url: str = os.getenv('AEMET_BASE_URL', 'https://opendata.aemet.es/opendata/api')
    aemet_api_key: str = os.getenv('AEMET_API_KEY', '')
    ria_base_url: str = os.getenv('RIA_BASE_URL', 'https://www.juntadeandalucia.es/agriculturaypesca/ifapa/riaws')
    ria_stations_url: str = os.getenv('RIA_STATIONS_URL', '')
    raif_crop_urls: dict[str, str] = field(default_factory=lambda: {
        'olivar': os.getenv(
            'RAIF_OLIVAR_URL',
            'https://www.juntadeandalucia.es/datosabiertos/portal/dataset/cdc8b852-6e4a-4336-9785-606fbbdc2243/resource/74062bbf-8391-460b-97c3-3aec55be5d77/download/raif_olivar_andalucia_2006_2026-14.zip',
        ),
    })
    mapa_catalog_path: str = os.getenv('MAPA_CATALOG_PATH', '')
    environment: str = os.getenv('ENVIRONMENT', 'development')
    risk_snapshot_retention_days: int = int(os.getenv('RISK_SNAPSHOT_RETENTION_DAYS', '365'))


settings = Settings()
