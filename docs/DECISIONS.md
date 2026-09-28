# Decisiones técnicas de AgroAlerta

Este documento registra decisiones arquitectónicas relevantes para que el código y su evolución mantengan una trazabilidad común.

## ADR-001 — Separación entre riesgo y alerta
**Estado:** aceptado

El motor agronómico calcula riesgo; un componente separado decide si ese cálculo genera un evento de alerta. Esto permite consultar riesgo sin crear eventos y probar ambas responsabilidades de forma independiente.

## ADR-002 — Meteorología real con estado explícito de disponibilidad
**Estado:** aceptado

Las observaciones RIA se almacenan con fuente y fecha. Cuando no existe evidencia meteorológica reciente, la API debe comunicar que no está disponible en lugar de fabricar valores.

## ADR-003 — Selección de estaciones RIA por proximidad
**Estado:** aceptado

Para una parcela se seleccionan las estaciones catalogadas más próximas dentro del radio operativo. El contexto combina hasta tres estaciones recientes mediante ponderación inversa de la distancia.

## ADR-004 — Documentación obligatoria de cambios relevantes
**Estado:** aceptado

Todo cambio técnico relevante debe dejar constancia de intención, impacto y validación en el propio repositorio. Esta regla evita que decisiones importantes dependan exclusivamente del historial conversacional.

## ADR-005 — SQLite en desarrollo, PostgreSQL/PostGIS como evolución
**Estado:** aceptado

SQLite facilita pruebas y desarrollo inicial. La persistencia queda encapsulada para permitir evolucionar a PostgreSQL/PostGIS cuando aumenten concurrencia, volumen o necesidades geoespaciales.

## ADR-006 — CI como puerta de calidad
**Estado:** aceptado

El pipeline de GitHub Actions ejecuta pruebas backend y análisis/pruebas Flutter. Cuando el desarrollador no dispone de un entorno local, CI constituye la validación técnica remota y sus fallos deben corregirse antes de considerar terminado el cambio.

## ADR-007 — No recalcular riesgo con meteorología obsoleta
**Estado:** aceptado

La ingesta puede persistir una observación sin que exista contexto meteorológico reciente. Antes de recalcular riesgo, el refresh construye el contexto usando la ventana de frescura del dominio. Si no hay evidencia disponible, se registra el motivo y se omite el recálculo y la generación de alertas para esa iteración.

**Consecuencia:** evitamos señales aparentemente actuales sustentadas en datos obsoletos. La parcela espera al siguiente ciclo con evidencia reciente.

## ADR-008 — Deduplificación de estaciones y registros XML
**Estado:** aceptado

El selector meteorológico deduplica estaciones por fuente y código, conservando la observación más reciente. El parser RAIF ignora nodos contenedores XML que no contienen campos de un registro. Estas reglas evitan duplicados y registros vacíos derivados de la estructura física de las fuentes.


## ADR-009 — CI como validación cuando no hay entorno local
**Estado:** aceptado

Cuando el desarrollador no dispone temporalmente de un entorno local para ejecutar VS Code, las pruebas no se posponen por defecto: se ejecutan en GitHub Actions y se corrigen sus resultados. La validación local queda como comprobación adicional cuando vuelva a estar disponible.
