from datetime import datetime, timedelta, timezone

from app.core.storage import Storage
from app.schemas import Parcel, ParcelCreate


def _parcel() -> Parcel:
    now = datetime.now(timezone.utc)
    return Parcel(
        id="parcel-1",
        owner_id="owner-1",
        label="Finca Norte",
        latitude=37.3,
        longitude=-5.9,
        crop_type="olivar",
        comarca="Campiña",
        created_at=now,
        updated_at=now,
    )


def test_update_parcel_rejects_stale_version(tmp_path, monkeypatch):
    monkeypatch.setenv("AGROALERTA_DB_PATH", str(tmp_path / "agroalerta.db"))
    storage = Storage()
    parcel = _parcel()
    storage.create_parcel(parcel)

    payload = ParcelCreate(
        label="Finca modificada",
        latitude=parcel.latitude,
        longitude=parcel.longitude,
        crop_type=parcel.crop_type,
        comarca=parcel.comarca,
    )
    stale = parcel.updated_at - timedelta(seconds=1)

    updated = storage.update_parcel(
        parcel.id,
        payload,
        parcel.owner_id,
        expected_updated_at=stale,
    )

    assert updated is None
    current = storage.get_parcel(parcel.id, parcel.owner_id)
    assert current is not None
    assert current.label == parcel.label


def test_update_parcel_accepts_current_version(tmp_path, monkeypatch):
    monkeypatch.setenv("AGROALERTA_DB_PATH", str(tmp_path / "agroalerta.db"))
    storage = Storage()
    parcel = _parcel()
    storage.create_parcel(parcel)

    payload = ParcelCreate(
        label="Finca actualizada",
        latitude=parcel.latitude,
        longitude=parcel.longitude,
        crop_type=parcel.crop_type,
        comarca=parcel.comarca,
    )
    updated = storage.update_parcel(
        parcel.id,
        payload,
        parcel.owner_id,
        expected_updated_at=parcel.updated_at,
    )

    assert updated is not None
    assert updated.label == "Finca actualizada"
    assert updated.updated_at > parcel.updated_at
