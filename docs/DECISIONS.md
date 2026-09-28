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


## ADR-010 — La interfaz no puede presentar datos agronómicos ficticios

**Estado:** aceptado  
**Fecha:** 2026-09-28

### Contexto
La capa Flutter contenía valores de demostración visibles en inicio, detalle de alertas y fallback de parcelas. En una aplicación agrícola operativa, esos valores pueden confundirse con observaciones reales y contaminar la interpretación del riesgo.

### Decisión
- El inicio consume alertas y parcelas persistidas mediante sus providers.
- El detalle de alerta muestra únicamente el nivel y puntuación de un evento persistido.
- Las variables meteorológicas no disponibles se presentan explícitamente como “No disponible”.
- Se elimina el fallback de parcelas ficticias y coordenadas de demostración.
- Los estados vacíos, errores y falta de evidencia se muestran como estados de disponibilidad, no como valores estimados inventados.

### Consecuencia
La interfaz puede parecer menos completa cuando no existen datos, pero conserva trazabilidad y evita presentar información sintética como si fuera evidencia agronómica.


## ADR-011 — Deduplicación estable de transiciones de riesgo

**Estado:** aceptado  
**Fecha:** 2026-09-28

### Contexto
Una alerta no debe duplicarse por volver a ejecutar el mismo ciclo. Usar únicamente la hora del cálculo como clave hacía que la deduplicación dependiera de cuándo se ejecutase el proceso.

### Decisión
La clave de deduplicación combina parcela, enfermedad, motivo de transición, nivel actual y la instantánea anterior que originó la transición. El primer riesgo usa la identidad estable initial.

### Consecuencia
Reintentos del mismo evento no crean otra alerta, mientras que una nueva transición posterior sí puede generar un nuevo evento legítimo.


### ADR-012: Notificación local de FCM en foreground

**Estado:** aceptado

**Contexto:** Firebase Cloud Messaging entrega correctamente el evento al dispositivo, pero los mensajes con payload de notificación no deben depender del comportamiento del sistema cuando la aplicación está abierta.

**Decisión:** registrar `FirebaseMessaging.onMessage` cuando Firebase esté disponible y convertir únicamente los mensajes recibidos en foreground con los campos `disease_code`, `parcel_id` y `risk_level` en una notificación local mediante `NotificationService`.

**Consecuencia:** las alertas permanecen visibles cuando AgroAlerta está abierta. En background/terminada se mantiene el comportamiento nativo de FCM para el payload de notificación. No se crea una segunda alerta de dominio: la notificación local es únicamente presentación del evento persistido.

**Validación pendiente:** prueba en dispositivos Android/iOS reales con permisos concedidos y revocados.


### ADR-013: Orquestación explícita del ciclo agroclimático

**Estado:** aceptado

**Decisión:** centralizar el orden operativo en `backend/app/jobs/agroclimatic_cycle.py`: catálogo RIA → RAIF por cultivo → meteorología por parcela → riesgo/alertas. Las fuentes auxiliares se aíslan ante errores y el ciclo no inventa evidencia cuando una fuente no está disponible.

**Motivo:** evita que cada mecanismo de ejecución implemente su propio orden y reduce el riesgo de calcular riesgo con catálogos o evidencias desactualizados.

**Operación:** el módulo es invocable como tarea Python y queda preparado para conectarse a un scheduler externo. No se introduce un scheduler embebido en FastAPI para evitar ejecuciones duplicadas cuando existen varias réplicas del servicio.

**Pendiente:** conectar este ciclo a el mecanismo de scheduling del entorno de producción, con control de concurrencia, timeout, reintentos y observabilidad.


### ADR-014: Endurecimiento de SQLite para concurrencia

**Estado:** aceptado

**Decisión:** mientras SQLite siga siendo el almacenamiento de desarrollo, todas las conexiones usarán timeout de 30 s, `busy_timeout`, WAL y foreign keys.

**Motivo:** el API y el ciclo agroclimático pueden ejecutarse en procesos separados. La configuración por defecto de SQLite aumenta el riesgo de errores de bloqueo y no aplica explícitamente integridad referencial.

**Límite:** esto no convierte SQLite en una base de datos de producción multi-réplica. La evolución prevista sigue siendo PostgreSQL/PostGIS para producción.

**Validación:** prueba automatizada de los pragmas y CI.


### ADR-015: Configuración explícita del almacenamiento

**Estado:** aceptado

**Decisión:** el almacenamiento recibe `AGROALERTA_DB_URL`, manteniendo `AGROALERTA_DB_PATH` como compatibilidad para SQLite. En esta etapa solo se acepta SQLite; una URL de otro motor falla explícitamente.

**Motivo:** separar configuración de persistencia del código permite preparar la migración a PostgreSQL/PostGIS sin introducir una dependencia de driver a medias ni comportamientos ambiguos.

**Consecuencia:** todavía no existe un adaptador PostgreSQL. El fallo explícito evita creer que una URL PostgreSQL está soportada cuando no lo está.

**Validación:** pruebas para URL SQLite y rechazo de drivers no implementados.
