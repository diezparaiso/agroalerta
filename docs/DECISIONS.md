# Decisiones de arquitectura

## ADR-001 — Separación entre riesgo y alerta

**Estado:** aceptada.

El motor calcula `DiseaseRisk`; la decisión de evento se realiza mediante `RiskAlertDecision`; las alertas se persisten y el endpoint de consulta solo las lee. Esto evita efectos secundarios al consultar historial.

## ADR-002 — Meteorología real con estado explícito

**Estado:** aceptada.

Cuando no existe evidencia meteorológica válida, el sistema devuelve ausencia explícita en lugar de valores de demostración. Los datos obsoletos no deben tratarse como actuales.

## ADR-003 — Estaciones RIA por proximidad

**Estado:** aceptada.

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
