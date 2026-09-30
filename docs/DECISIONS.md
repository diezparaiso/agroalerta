# Decisiones de arquitectura

## ADR-001 — Separación entre riesgo y alerta

**Estado:** aceptada.

El motor calcula `DiseaseRisk`; la decisión de evento se realiza mediante `RiskAlertDecision`; las alertas se persisten y el endpoint de consulta solo las lee. Esto evita efectos secundarios al consultar historial.

## ADR-002 — Meteorología real con estado explícito

**Estado:** aceptada.

Cuando no existe evidencia meteorológica válida, el sistema devuelve ausencia explícita en lugar de valores de demostración. Los datos obsoletos no deben tratarse como actuales.

## ADR-003 — Estaciones RIA por proximidad

**Estado:** modificada por ADR-007.

Se mantiene un catálogo canónico de estaciones RIA y se seleccionan hasta tres estaciones activas por distancia, con límite máximo de 80 km. Las observaciones recientes se combinan mediante ponderación por distancia.

## ADR-004 — Documentación obligatoria por cambio

**Estado:** aceptada.

AgroAlerta combina software, fuentes agronómicas, modelos de riesgo y notificaciones. Todo cambio relevante debe registrar intención, decisión, impacto y validación para conservar la memoria técnica del proyecto.

## ADR-005 — SQLite de desarrollo y evolución a PostgreSQL/PostGIS

**Estado:** aceptada.

SQLite simplifica el MVP y las pruebas. La arquitectura de persistencia debe permitir evolucionar a PostgreSQL/PostGIS para concurrencia, escalado y consultas geoespaciales.

## ADR-006 — CI como puerta de calidad

**Estado:** aceptada.

CI ejecuta backend y Flutter en cada push y pull request. El resultado de CI forma parte de la validación del cambio y los fallos relevantes deben corregirse antes de construir capas dependientes.

## ADR-007 — Meteorología real: RIA/IFAPA primero, AEMET de respaldo

**Estado:** aceptada. Modifica la selección de estaciones descrita en el ADR-003.

El endpoint `GET /api/v1/weather/{parcel_id}` consulta las fuentes en este orden:

1. **RIA/IFAPA** (sin credenciales): estación activa no plástica más próxima a la parcela mediante distancia haversine sobre el catálogo en vivo de `GET {ria_base_url}/estaciones`, y observaciones de `GET {ria_base_url}/datosdiarios/forceEt0/{provincia}/{estacion}/{desde}/{hasta}`.
2. **AEMET** (solo si existe `AEMET_API_KEY`): estación meteorológica de la capital andaluza del INE más próxima a la parcela. Es una aproximación documentada, no la estación real más cercana.
3. Si ninguna fuente está disponible o responde, se devuelve **HTTP 503** con el motivo real. Nunca se inventan valores, en línea con el ADR-002 y la regla 3 de `docs/ENGINEERING_GUIDELINES.md`.

La respuesta conserva `temperature_c`, `relative_humidity`, `rainfall_mm_24h`, `station_distance_km` y `observed_at`, y añade `station_name` y `source` (`ria-ifapa` o `aemet`) para que el cliente sepa de dónde procede cada observación.

**Respecto al ADR-003:** esta primera versión implementada usa el catálogo en vivo de estaciones (no un catálogo canónico en repositorio) y selecciona únicamente la estación más próxima, sin límite de 80 km ni combinación ponderada de hasta tres estaciones. Esas ampliaciones quedan como evolución pendiente; el cambio de alcance se registra aquí conforme al ADR-004.

**Validación (2026-09-30):** 9 pruebas nuevas en `backend/tests/test_weather_service.py` (31 en total, todas en verde), prueba en vivo contra RIA/IFAPA con datos reales y ninguna incidencia de `flutter analyze` en los archivos tocados. AEMET no ha podido probarse en vivo por falta de `AEMET_API_KEY`.
