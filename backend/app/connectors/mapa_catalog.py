import csv
from datetime import datetime, timezone
from pathlib import Path

from app.schemas import Product


def load_catalog(path: str | Path) -> list[Product]:
    """Carga una exportacion CSV validada del registro MAPA.

    El scraping del buscador oficial no se realiza en peticiones de usuario.
    """
    catalog_path = Path(path)
    if not catalog_path.exists():
        return []
    snapshot = datetime.now(timezone.utc)
    with catalog_path.open(newline='', encoding='utf-8') as handle:
        return [
            Product(
                id=row['id'],
                commercial_name=row['commercial_name'],
                active_substance=row['active_substance'],
                dose=row['dose'],
                safety_period_days=int(row['safety_period_days']),
                crop_type=row['crop_type'],
                disease_code=row['disease_code'],
                mapa_snapshot_date=snapshot,
            )
            for row in csv.DictReader(handle)
        ]
