from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree as ET

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class RaifRecord:
    source_code: str
    external_id: str
    observed_at: datetime | None
    province: str | None
    municipality: str | None
    parcel: str | None
    latitude: float | None
    longitude: float | None
    payload: dict[str, Any]


class RaifClient:
    """Descarga y normaliza los ficheros XML publicados por RAIF."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=60)

    async def download_crop_zip(self, crop: str = "olivar") -> bytes:
        url = settings.raif_crop_urls.get(crop)
        if not url:
            raise ValueError(f"No hay recurso RAIF configurado para {crop}")
        response = await self.client.get(url)
        response.raise_for_status()
        return response.content

    def parse_zip(self, content: bytes, crop: str = "olivar") -> list[RaifRecord]:
        records: list[RaifRecord] = []
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for name in archive.namelist():
                if not name.lower().endswith(".xml"):
                    continue
                xml_bytes = archive.read(name)
                records.extend(self._parse_xml(xml_bytes, crop, name))
        return records

    def _parse_xml(self, content: bytes, crop: str, filename: str) -> list[RaifRecord]:
        root = ET.fromstring(content)
        records: list[RaifRecord] = []

        for element in root.iter():
            children = list(element)
            if not children:
                continue
            fields = {}
            for child in children:
                key = self._clean_key(child.tag)
                value = "".join(child.itertext()).strip()
                if value:
                    fields[key] = value
            if not fields:
                continue

            province = self._pick(fields, "PROVINCIA")
            municipality = self._pick(fields, "MUNICIPIO", "MUNICIPIO_NOMBRE")
            parcel = self._pick(fields, "PARCELA", "CODIGO_PARCELA")
            latitude = self._parse_float(self._pick(fields, "LATITUD", "LATITUDE", "LAT"))
            longitude = self._parse_float(self._pick(fields, "LONGITUD", "LONGITUDE", "LON", "LONG"))
            observed_at = self._parse_date(
                self._pick(fields, "FECHA", "FECHA_MUESTREO", "FECHA_MUESTREO")
            )
            external_id = "|".join(
                [crop, province or "", municipality or "", parcel or "", observed_at.isoformat() if observed_at else ""]
            )
            records.append(
                RaifRecord(
                    source_code="raif_fitosanitario",
                    external_id=external_id,
                    observed_at=observed_at,
                    province=province,
                    municipality=municipality,
                    parcel=parcel,
                    latitude=latitude,
                    longitude=longitude,
                    payload={"crop": crop, "file": filename, "fields": fields},
                )
            )
        return records

    @staticmethod
    def _clean_key(value: str) -> str:
        return re.sub(r"[^A-Z0-9_]", "", value.upper().split("}")[-1])

    @staticmethod
    def _pick(fields: dict[str, str], *keys: str) -> str | None:
        for key in keys:
            value = fields.get(key)
            if value:
                return value
        return None

    @staticmethod
    def _parse_float(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return float(value.replace(',', '.'))
        except ValueError:
            return None

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value[:19], fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None
