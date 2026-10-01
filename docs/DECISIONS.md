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

## ADR-007 — Consultas externas asíncronas, caché y carga progresiva

**Estado:** aceptada.

Las llamadas a proveedores externos no deben bloquear la navegación ni provocar que una pantalla espere a todas las fuentes. La API y el cliente aplicarán tiempos máximos, límites de concurrencia, errores por fuente y cargas en segundo plano cuando proceda. La interfaz mostrará estados de carga con lenguaje claro, permitirá reintentar y mostrará datos guardados cuando existan, señalando su antigüedad. Las respuestas se almacenarán en caché con claves que incluyan fuente, ubicación/parcela, intervalo temporal y versión de parámetros; la caducidad dependerá de la frecuencia y naturaleza de cada fuente. Las solicitudes idénticas deben deduplicarse cuando sea posible. Los datos simulados no se utilizarán como sustituto silencioso de una fuente fallida.

**Impacto:** menor latencia percibida, menos llamadas duplicadas y mejor tolerancia a fallos. La caché local de meteorología del cliente es un primer paso, no una solución completa multiusuario. Se deberá añadir caché compartida en backend y trabajos de actualización programada antes de aumentar el volumen de consultas externas.
