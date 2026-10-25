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

El clima usa datos reales: consulta primero la estación RIA-IFAPA activa más cercana a la parcela y, si no responde, la predicción AEMET del municipio de referencia (requiere `AEMET_API_KEY`). Devuelve `parcel_id`, `temperature_c`, `relative_humidity`, `rainfall_mm_24h`, `station_distance_km`, `observed_at`, `station_name` y `source` (`ria-ifapa` o `aemet`). Con `source: aemet`, `rainfall_mm_24h`, `station_name` y `station_distance_km` pueden ser `null` (el diario de AEMET no publica milímetros y es predicción municipal, no estación). Si ninguna fuente está disponible responde `503` con el motivo; nunca devuelve valores ficticios.

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
- `503`: fuente externa de clima (RIA-IFAPA o AEMET) sin datos; el `detail` explica el motivo.


## Operación agronómica

- `GET /api/v1/farm/center`
  - Devuelve el estado operativo agregado de las parcelas, sensores, telemetría, riesgos y eventos recientes.

## Campañas y resultados

- `POST /api/v1/parcels/{parcel_id}/campaigns`
- `GET /api/v1/parcels/{parcel_id}/campaigns`
- `PATCH /api/v1/campaigns/{campaign_id}/status`
- `GET /api/v1/campaigns/{campaign_id}/summary`
- `GET /api/v1/campaigns/{campaign_id}/decisions`
- `POST /api/v1/campaigns/{campaign_id}/results`
- `GET /api/v1/campaigns/{campaign_id}/results`
- `GET /api/v1/campaigns/{campaign_id}/results/summary`

La interfaz Flutter consume estos contratos sin duplicar reglas de dominio: el backend mantiene las validaciones de parcela, cultivo, fechas, campaña activa y cálculo de rendimiento.

## Actividades y línea de tiempo

> MODIFICADO POR OPENCODE (Fase 2, 2026-10-05): endpoints verificados en vivo y añadidos al contrato; antes no estaban documentados.

- `POST /api/v1/parcels/{parcel_id}/activities` → `201`.
- `GET /api/v1/parcels/{parcel_id}/activity-timeline` → `200` lista.

Alta de actividad:

```json
{
  "parcel_id": "uuid",
  "activity_type": "labor",
  "title": "Abonado de fondo",
  "detail": "opcional",
  "occurred_at": "2026-09-30T21:00:00Z",
  "quantity": null,
  "unit": null
}
```

`activity_type` admite `labor`, `irrigation`, `treatment`, `observation`, `harvest` (los mismos literales que envía `activity_timeline_screen.dart`). `title` es obligatorio (1-160); `detail`, `quantity` y `unit` son opcionales. El timeline admite `?limit=1..300` (por defecto 100).

## Riego

> MODIFICADO POR OPENCODE (Fase 2, 2026-10-05): verificado en vivo. **Antes devolvía `500`** porque la tabla `irrigation_events` no existía en `Storage`; corregido y cubierto con tests.

- `POST /api/v1/parcels/{parcel_id}/irrigation/events` → `201`.
- `GET /api/v1/parcels/{parcel_id}/irrigation/events?limit=100` → `200` lista.
- `GET /api/v1/parcels/{parcel_id}/irrigation/intelligence?window_days=7` → `200`.

Evento de riego:

```json
{
  "parcel_id": "uuid",
  "started_at": "2026-10-03T08:00:00Z",
  "duration_minutes": 90,
  "water_liters": 4200.0,
  "method": "goteo",
  "notes": "Riego de la mañana",
  "campaign_id": null
}
```

`duration_minutes` es obligatorio (1-1440). `method` es texto libre de 1-80 caracteres (p. ej. `goteo`, `aspersion`, `manto`); `water_liters`, `campaign_id` y `notes` son opcionales.

Inteligencia de riego (respuesta):

```json
{
  "parcel_id": "uuid",
  "window_days": 7,
  "event_count": 1,
  "total_water_liters": 4200.0,
  "average_daily_water_liters": 600.0,
  "latest_irrigation_at": "2026-10-03T08:00:00Z",
  "latest_soil_moisture": null,
  "water_use_level": "bajo",
  "soil_status": "sin_datos",
  "action": "vigilar",
  "explanation": "texto orientativo",
  "evidence": ["..."]
}
```

Sin eventos recientes la respuesta sigue siendo `200` con `event_count: 0` y `action: registrar`: el backend expresa ausencia de datos, nunca inventa recomendaciones.

## Decisión agronómica

> MODIFICADO POR OPENCODE (Fase 2, 2026-10-05): verificado en vivo y documentado.

- `GET /api/v1/agronomic-decision/{parcel_id}/{disease_code}?campaign_id=uuid` → `200`.

`disease_code` admite `repilo` y `mildiu` (`422` con otro valor; `404` si no aplica al cultivo de la parcela). Si se pasa `campaign_id`, la decisión queda registrada en la campaña (`404` si la campaña no existe o pertenece a otra parcela). Devuelve `priority` (`informativa`/`vigilar`/`revisar`), `decision_score`, `confidence`, `headline`, `explanation`, `next_steps` y `evidence` (lista de señales con fuente, clave, valor y peso). No prescribe productos ni dosis.

## Autenticación y autorización

> MODIFICADO POR OPENCODE (Fase 2, 2026-10-05): matriz verificada en vivo con **77 comprobaciones, 0 fallos**.

Comportamiento observado:

| Situación | Respuesta |
|---|---|
| Sin cabecera `Authorization` (desarrollo) | `200` con `owner_id: anonymous` (datos compartidos) |
| Sin cabecera `Authorization` (`ENVIRONMENT=production`) | `401 Autenticacion requerida` |
| Cabecera mal formada (`Basic …`, `Bearer` vacío) | `401 Token Bearer invalido` |
| Token arbitrario en desarrollo (sin `FIREBASE_SERVICE_ACCOUNT_JSON`) | Se acepta y se usa como `owner_id` |
| Token con Firebase Admin activo y inválido | `401 Token Firebase invalido` |
| Token con Firebase Admin activo pero sin credenciales (`ENVIRONMENT=production`) | `503` |

Aislamiento entre usuarios (usuario A vs usuario B, verificado en vivo): B obtiene `404` al leer, modificar o borrar parcelas, clima, riesgo, historial, dispositivos, telemetría, informes, campañas, resumen, actividades, línea de tiempo, decisión, riego, resultados, y al cambiar el estado de la campaña; y sus listados globales (`/alerts`, `/farm/center`) no contienen recursos de A. El borrado de push token de otro usuario no tiene efecto (`204` idempotente sin eliminar la fila).

**Riesgos documentados (sin cambiar el modelo de auth, decisión pendiente del usuario):**

1. En desarrollo no se valida la autenticidad del token: quien conozca el `owner_id` de otro usuario puede leer sus datos. El aislamiento real depende de que los ID tokens de Firebase sean opacos (lo son) y de activar `ENVIRONMENT=production` + `FIREBASE_SERVICE_ACCOUNT_JSON` en despliegue.
2. Todos los clientes sin token comparten el mismo espacio `anonymous` en desarrollo.
3. La verificación con Firebase Admin **no se ha podido probar en vivo** por falta de credenciales (pendiente del usuario).

## Fuentes de datos y conectores

> MODIFICADO POR OPENCODE (Fase 2, 2026-10-05/06).

- El backend solo usa datos reales. Si no hay datos, responde `503` con el motivo; jamás devuelve valores ficticios (ADR-007).
- La tarjeta de clima de la app muestra la fuente (`Fuente: ria-ifapa` / `Fuente: aemet`).
- **Reintentos**: los conectores AEMET y RIA/IFAPA usan un máximo de 3 intentos (2 reintentos) con espera creciente (0,5 s → 1 s, o `Retry-After` si el servidor lo indica), y **solo** ante timeout, `5xx` o `429`. Cualquier otro fallo se propaga sin reintentar para no consumir cuota (`app/connectors/http_retry.py`).
- **Caché**: clima por ubicación 10 min, estaciones RIA 24 h, predicción AEMET por municipio 6 h (`weather_service.py`). Verificado en vivo: segunda consulta AEMET 0,0001 s sin salir a la red.
- Verificación en vivo 2026-10-05: RIA-IFAPA estación *La Rinconada* a 9,4 km (0,98 s) y AEMET municipio de Sevilla (0,78 s) devuelven datos reales; municipio inexistente falla en 0,09 s sin reintentos.
