from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

def build_irrigation_intelligence(parcel_id: str, irrigation_events: list[dict[str, Any]], latest_telemetry: dict[str, Any] | None, window_days: int = 7) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    recent = [e for e in irrigation_events if _date(e.get('started_at')) >= cutoff]
    volumes = [float(e['water_liters']) for e in recent if e.get('water_liters') is not None]
    total = round(sum(volumes), 2)
    daily = round(total / window_days, 2)
    soil = _number((latest_telemetry or {}).get('soil_moisture'))
    soil_status = 'sin_datos' if soil is None else 'seco' if soil < 30 else 'humedo' if soil > 75 else 'adecuado'
    use = 'sin_datos' if not recent else 'alto' if daily >= 5000 else 'moderado' if daily >= 1500 else 'bajo'
    if not recent:
        action, explanation = 'registrar', 'No hay riegos recientes registrados; registra los eventos para construir un histórico útil.'
    elif soil_status == 'seco':
        action, explanation = 'revisar', 'La humedad de suelo reciente es baja; revisa el estado del cultivo y la programación de riego antes de actuar.'
    elif soil_status == 'humedo' and use == 'alto':
        action, explanation = 'revisar', 'Hay humedad elevada y un consumo registrado alto; revisa drenaje, frecuencia y mediciones del sensor.'
    elif soil_status == 'sin_datos':
        action, explanation = 'vigilar', 'Hay histórico de riego, pero falta una lectura reciente de humedad de suelo.'
    else:
        action, explanation = 'vigilar', 'El histórico de riego y la lectura de humedad no muestran una señal que requiera revisión inmediata.'
    evidence = [f'{len(recent)} evento(s) de riego en {window_days} días', f'{total:.1f} L registrados con volumen' if volumes else 'No hay volúmenes de agua registrados']
    if soil is not None: evidence.append(f'Humedad de suelo más reciente: {soil:.1f}%')
    return {'parcel_id': parcel_id, 'window_days': window_days, 'event_count': len(recent), 'total_water_liters': total, 'average_daily_water_liters': daily, 'latest_irrigation_at': max((_date(e.get('started_at')) for e in recent), default=None), 'latest_soil_moisture': soil, 'water_use_level': use, 'soil_status': soil_status, 'action': action, 'explanation': explanation, 'evidence': evidence}

def _date(value: object) -> datetime:
    try: value = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (TypeError, ValueError): return datetime.min.replace(tzinfo=timezone.utc)
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool): return None
    try: return float(value)
    except (TypeError, ValueError): return None
