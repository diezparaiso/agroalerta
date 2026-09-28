from app.connectors.raif_client import RaifClient
from app.core.storage import Storage


async def ingest_raif(crop: str = "olivar") -> dict[str, int | str]:
    """Descarga el dataset RAIF configurado y persiste evidencias normalizadas."""
    client = RaifClient()
    storage = Storage()
    content = await client.download_crop_zip(crop)
    records = client.parse_zip(content, crop)
    saved = 0
    for record in records:
        if storage.save_source_record(
            source_code=record.source_code,
            external_id=record.external_id,
            observed_at=record.observed_at,
            province=record.province,
            municipality=record.municipality,
            parcel_reference=record.parcel,
            payload=record.payload,
        ):
            saved += 1
    return {"status": "ingested", "crop": crop, "records": saved}
