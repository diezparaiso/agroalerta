from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz del repositorio: backend/app/core/config.py -> parents[3]
_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Configuracion del backend.

    Prioridad (pydantic-settings): argumentos de inicializacion > variables de
    entorno > fichero `.env` en la raiz del proyecto > valores por defecto.
    El fichero `.env` es opcional; si no existe, todo funciona con defaults.
    """

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
        frozen=True,
    )

    aemet_base_url: str = 'https://opendata.aemet.es/opendata/api'
    aemet_api_key: str = ''
    ria_base_url: str = 'https://www.juntadeandalucia.es/agriculturaypesca/ifapa/riaws'
    environment: str = 'development'
    risk_snapshot_retention_days: int = 365


settings = Settings()
