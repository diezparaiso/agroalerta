import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    aemet_base_url: str = os.getenv('AEMET_BASE_URL', 'https://opendata.aemet.es/opendata/api')
    aemet_api_key: str = os.getenv('AEMET_API_KEY', '')
    ria_base_url: str = os.getenv('RIA_BASE_URL', 'https://www.juntadeandalucia.es/agriculturaypesca/ifapa/riaws')
    siar_base_url: str = os.getenv('SIAR_BASE_URL', '')
    siar_daily_path: str = os.getenv('SIAR_DAILY_PATH', '')
    siar_api_key: str = os.getenv('SIAR_API_KEY', '')
    copernicus_api_url: str = os.getenv('COPERNICUS_API_URL', 'https://cds.climate.copernicus.eu/api')
    copernicus_api_key: str = os.getenv('COPERNICUS_API_KEY', '')
    environment: str = os.getenv('ENVIRONMENT', 'development')
    risk_snapshot_retention_days: int = int(os.getenv('RISK_SNAPSHOT_RETENTION_DAYS', '365'))


settings = Settings()
