# Contratos API

Base local: `http://localhost:8000`

Los endpoints de recursos aceptan `Authorization: Bearer <firebase-id-token>`. En desarrollo, sin Firebase configurado, se usa el propietario `anonymous`.

## Salud

- `GET /health`
  - Comprueba SQLite y devuelve `status`, `service` y `version`.
- `GET /health/integrations`
  - Devuelve estado seguro de AEMET, RIA/IFAPA, Firebase Admin y MAPA.
- `GET /health/metrics`
  - Devuelve contador y latencia media por ruta.

## Parcelas

- `GET /api/v1/parcels`
- `POST /api/v1/parcels`
- `GET /api/v1/parcels/{parcel_id}`
- `PUT /api/v1/parcels/{parcel_id}`
- `DELETE /api/v1/parcels/{parcel_id}`

Alta:

```json
{
  "label": "Olivar norte",
  "latitude": 37.39,
  "longitude": -5.99,
  "crop_type": "olivar",
  "comarca": "Campina de Sevilla"
}
```

`crop_type` admite `olivar` o `vinedo`. Las parcelas se filtran por `owner_id`.

## Clima y riesgo

- `GET /api/v1/weather/{parcel_id}`
- `GET /api/v1/disease-risk/{parcel_id}`
- `GET /api/v1/alerts`
- `GET /api/v1/risk-history/{parcel_id}?limit=100&offset=0`

El riesgo devuelve puntuación, nivel, confianza, variables utilizadas, fechas y recomendación orientativa.

## Productos y reportes

- `GET /api/v1/products?crop_type=olivar&disease_code=repilo`
- `POST /api/v1/field-reports`

```json
{
  "parcel_id": "uuid",
  "type": "sintoma",
  "photo_url": "https://storage.example/report.jpg",
  "count": 2,
  "notes": "Manchas en hojas bajas",
  "latitude": 37.39,
  "longitude": -5.99,
  "reported_at": "2026-09-27T10:00:00Z"
}
```

## IoT

- `POST /api/v1/devices`
- `GET /api/v1/devices/{parcel_id}`
- `POST /api/v1/telemetry`
- `GET /api/v1/telemetry/{parcel_id}`

Telemetría:

```json
{
  "parcel_id": "uuid",
  "device_id": "sensor-001",
  "temperature_c": 18.4,
  "relative_humidity": 87,
  "leaf_wetness_hours": 18,
  "soil_moisture": 42,
  "battery_percent": 91,
  "measured_at": "2026-09-27T10:00:00Z"
}
```

## Notificaciones

- `POST /api/v1/push-tokens`
- `DELETE /api/v1/push-tokens/{token}`

Los tokens se guardan por propietario y se eliminan cuando fallan los envíos tras reintentos.

## Errores

- `400`: payload inválido.
- `401`: token Bearer inválido cuando Firebase Admin está activo.
- `404`: recurso inexistente o perteneciente a otro usuario.
- `422`: validación Pydantic fallida.
- `500`: error interno; revisar métricas y logs sin exponer secretos.


## Contexto espacial

### GET /api/v1/spatial-context/{parcel_id}

Devuelve evidencias fitosanitarias georreferenciadas de las fuentes disponibles dentro de un radio configurable.

Query:
- `radius_km`: 1..100, por defecto 25.

La respuesta conserva la distancia calculada a la parcela y la trazabilidad de la evidencia. Actualmente solo se incluyen registros RAIF que publiquen coordenadas; los registros sin coordenadas no se fuerzan a una posición estimada.
