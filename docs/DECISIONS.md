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


### ADR-016: Versionado explícito del esquema SQLite

**Estado:** aceptado

**Decisión:** el almacenamiento registra versiones aplicadas en `schema_migrations`. El esquema actual queda identificado como versión 1.

**Motivo:** las modificaciones anteriores eran idempotentes, pero no dejaban trazabilidad de qué versión de esquema estaba instalada. El versionado permite introducir futuras migraciones incrementales sin depender únicamente de `CREATE TABLE IF NOT EXISTS` y comprobaciones de columnas.

**Alcance:** esta primera versión registra el esquema actual; no se inventa una migración histórica destructiva para instalaciones existentes. Las siguientes modificaciones de esquema deberán añadir una versión nueva y una prueba de upgrade.

**Validación:** se comprueba que una base nueva queda en versión 1 y que inicializar varias veces mantiene la misma versión.


### ADR-017: Publicidad AdMob configurable y segura por defecto

**Estado:** aceptado

**Decisión:** AgroAlerta integra banners mediante `google_mobile_ads`, pero el identificador de unidad publicitaria se obtiene exclusivamente de `ADMOB_BANNER_ID` en tiempo de compilación. Si no existe configuración, no se inicializa el SDK ni se muestra publicidad.

**Motivo:** evitar publicar accidentalmente el ID de anuncios de prueba de Google y separar el código de la aplicación de credenciales/configuración específica de monetización.

**Consentimiento:** el banner existente requiere aceptación explícita almacenada localmente antes de solicitar el anuncio. Antes de publicar en mercados regulados deberá sustituirse/completarse este mecanismo con la solución de consentimiento adecuada para la configuración de Google y la jurisdicción objetivo.

**Plataformas:** el repositorio actual no contiene todavía los proyectos nativos Android/iOS, por lo que quedan pendientes los App IDs nativos de AdMob y su configuración en `AndroidManifest.xml`/Info.plist cuando esos proyectos se incorporen.

**Validación:** el código queda inactivo cuando `ADMOB_BANNER_ID` no está definido y CI debe validar el build Flutter.


### ADR-018: Catálogo de productos sin datos ficticios

**Estado:** aceptado

**Decisión:** el endpoint de productos solo expone registros procedentes de un snapshot CSV configurado mediante `MAPA_CATALOG_PATH`. Si no existe catálogo configurado, devuelve una lista vacía y el cliente muestra explícitamente que el catálogo no está disponible.

**Motivo:** el producto fitosanitario, la sustancia, dosis y plazo de seguridad son datos regulados y no deben rellenarse con ejemplos sintéticos dentro de la aplicación.

**Importación:** `backend/app/connectors/mapa_catalog.py` sigue siendo el límite de entrada. La petición de usuario no realiza scraping ni descarga directamente del registro oficial.

**Pendiente:** automatizar la obtención/verificación del snapshot oficial vigente, conservar metadatos de fuente y fecha de descarga y ampliar filtros según el contrato oficial validado.


### ADR-019: Observaciones offline ancladas a la parcela real

**Estado:** aceptado

**Decisión:** los informes de campo enviados desde Flutter deben usar el identificador y las coordenadas reales de la parcela seleccionada. Si no hay parcela o sus coordenadas no son válidas, el envío se bloquea y se informa al usuario.

**Motivo:** una observación agronómica georreferenciada no puede caer en coordenadas Sevilla por defecto ni usar el nombre de la parcela como sustituto de un identificador persistente.

**Sincronización:** el servicio offline evita ejecuciones concurrentes de sincronización para no enviar dos veces la misma cola cuando se producen varios eventos de conectividad.

**Pendiente:** selector explícito de parcela en el formulario, estado de sincronización visible y estrategia de reintentos con backoff.

## ADR-020: Selección explícita de parcela en observaciones de campo

**Estado:** aceptado  
**Fecha:** 2026-09-28

**Contexto:** el formulario de observaciones ya utilizaba el identificador y coordenadas reales, pero escogía automáticamente la primera parcela disponible. Con varias parcelas, esa heurística podía asociar una observación válida a la parcela equivocada.

**Decisión:** el formulario exige seleccionar una parcela por su identificador persistente. El payload de la observación se construye desde esa parcela y conserva sus coordenadas reales. Si la parcela no tiene identidad persistente o coordenadas válidas, el payload se rechaza antes de enviarse o encolarse.

**Validación:** `test/features/reports/report_payload_test.dart` comprueba tanto el mapeo de identidad/coordenadas como el rechazo de parcelas incompletas.

**Consecuencia:** la observación queda vinculada a la parcela elegida por el usuario y no depende del orden de la lista local o remota.

**Pendiente:** mostrar estado de sincronización y añadir estrategia de reintentos con backoff para la cola offline.

## ADR-021: Reintentos offline con backoff por informe

**Estado:** aceptado  
**Fecha:** 2026-09-28

**Contexto:** la cola offline podía volver a intentar todos los informes ante cada evento de conectividad. Esto podía producir reintentos demasiado frecuentes cuando el backend o la red seguían fallando.

**Decisión:** cada informe conserva `attempts`, `last_attempt_at` y `next_attempt_at`. Los informes antiguos sin estos campos se normalizan con cero intentos y siguen siendo elegibles. Tras un fallo se aplica backoff exponencial: 30 segundos, 1 minuto, 2, 4, etc., con un máximo de 1 hora.

**Consecuencia:** una incidencia persistente no genera una tormenta de peticiones, mientras que un informe nuevo o pendiente por primera vez puede sincronizarse inmediatamente. El backoff es independiente por informe, por lo que un fallo no bloquea artificialmente los demás.

**Validación:** `test/features/reports/offline_retry_policy_test.dart` cubre elegibilidad, progresión exponencial, límite máximo y compatibilidad con registros antiguos.

## ADR-022: Estado visible de la cola offline

**Estado:** aceptado  
**Fecha:** 2026-09-28

**Contexto:** la cola de observaciones ya podía conservar informes y reintentarlos, pero la interfaz no informaba al agricultor de si existían pendientes ni de cuándo estaba previsto el siguiente intento.

**Decisión:** exponer un resumen de la cola mediante Riverpod y mostrarlo en el formulario de observaciones: número de pendientes, número con fallos previos y hora del siguiente reintento cuando existe. El estado se deriva exclusivamente de la cola persistida; no se inventa conectividad ni confirmación de entrega.

**Consecuencia:** el usuario puede distinguir entre una observación ya enviada y una observación todavía pendiente. El detalle operativo de red sigue perteneciendo al sincronizador y no al formulario.

**Validación:** `test/features/reports/offline_queue_status_test.dart` cubre conteos, reintentos pendientes y cola vacía.

## ADR-023: Idempotencia de observaciones offline

**Estado:** aceptado  
**Fecha:** 2026-09-28

**Contexto:** una observación de campo puede enviarse correctamente al servidor y, por una interrupción de red o respuesta perdida, permanecer en la cola local. Un reintento posterior no debe crear una segunda observación.

**Decisión:** cada observación se crea en Flutter con un `report_id` UUID persistente dentro del payload. La API acepta ese identificador y la tabla `field_reports` lo utiliza como clave primaria mediante inserción idempotente. Si el identificador ya existe, la API devuelve `already_received` y no duplica el registro.

**Consecuencia:** los reintentos son seguros frente a respuestas perdidas y reconexiones. La identidad de la observación pertenece al evento original, no a cada intento de transporte.

**Validación:** `backend/tests/test_field_report_idempotency.py` verifica que dos inserciones con el mismo identificador dejan un único registro; el test Flutter de payload verifica la generación del identificador.

## ADR-024: Control de concurrencia optimista para parcelas

**Estado:** aceptado  
**Fecha:** 2026-09-28

**Contexto:** una parcela puede ser leída en un dispositivo y modificada posteriormente desde otro contexto. Una actualización basada en una copia antigua no debe sobrescribir silenciosamente la versión más reciente.

**Decisión:** `updated_at` actúa como versión de la parcela. Las actualizaciones pueden enviar `expected_updated_at`; el backend solo modifica la fila si esa versión sigue siendo la actual. Si no coincide, responde HTTP 409 y no aplica cambios.

**Consecuencia:** los clientes pueden detectar un conflicto y volver a cargar la parcela antes de decidir cómo reconciliarla. Las llamadas antiguas que no envíen versión siguen funcionando por compatibilidad, pero los flujos offline nuevos deben usar control de versión.

**Validación:** `backend/tests/test_parcel_concurrency.py` cubre rechazo de versión obsoleta y aceptación de la versión actual.

## ADR-025: Resolución segura de conflictos en Flutter

**Estado:** aceptado  
**Fecha:** 2026-09-28

**Contexto:** el backend ya rechaza una actualización de parcela basada en una versión obsoleta mediante HTTP 409. El cliente no debe convertir ese conflicto en un error genérico ni generar una versión nueva por su cuenta.

**Decisión:** `ParcelSummary` conserva `updated_at` del servidor. El cliente envía esa versión como `expected_updated_at` al actualizar. Un 409 se transforma en `ParcelConflictException` y la edición local no se sobrescribe automáticamente. Una parcela sin versión conocida no puede entrar en un flujo de actualización seguro.

**Consecuencia:** el usuario puede conservar su edición y volver a cargar la versión actual antes de reconciliarla. La resolución automática de conflictos queda fuera de esta fase para evitar sobrescrituras silenciosas.

**Validación:** `test/features/parcels/parcel_concurrency_test.dart` verifica conservación de la versión y bloqueo de actualizaciones sin versión.

## ADR-026: Reconciliación explícita de conflictos de parcelas

**Estado:** aceptado  
**Fecha:** 2026-09-28

**Contexto:** un HTTP 409 evita sobrescrituras, pero un error técnico aislado deja al usuario sin una vía clara para resolver el conflicto.

**Decisión:** Flutter vuelve a cargar la versión remota y presenta al usuario una comparación mínima entre su edición y el estado del servidor. Puede cancelar, aceptar la versión remota o conservar su edición. Conservarla vuelve a intentar contra la nueva versión remota mediante control optimista; si vuelve a cambiar, se mantiene el conflicto y no se fuerza una escritura.

**Consecuencia:** la aplicación nunca decide silenciosamente qué versión debe prevalecer. La reconciliación automática de campos queda fuera de esta fase.

**Validación:** `test/features/parcels/parcel_conflict_test.dart` cubre detección de diferencias en el modelo de conflicto.


## ADR-027 — Dashboard visual basado únicamente en evidencia disponible

**Estado:** aceptado  
**Fecha:** 2026-09-28

**Contexto:** se definió una referencia visual para una pantalla inicial más clara: cabecera, indicadores, mapa, alertas y sensores. Además, persistía un fallback meteorológico con valores sintéticos en Flutter.

**Decisión:** el dashboard será responsive y mostrará únicamente datos procedentes de providers reales. La ausencia de evidencia se representa como `No disponible`. El mapa se centra usando coordenadas reales de parcelas y no utiliza una ubicación ficticia como Sevilla. Se añade una prueba específica para proteger el estado meteorológico sin evidencia.

**Validación:** `test/features/home/weather_provider_test.dart` cubre valores presentes y ausencia de fallback ficticio. CI debe validar análisis y pruebas Flutter.

**Consecuencia:** la interfaz puede verse más vacía cuando no existen datos reales, pero mantiene la trazabilidad agronómica.


## ADR-028 — Compatibilidad Android del plugin AdMob

**Estado:** aceptado  
**Fecha:** 2026-09-28

La primera compilación Android reproducible mostró que `google_mobile_ads 5.3.1` falla al configurarse con el Gradle generado por la versión estable de Flutter usada por CI. En lugar de degradar la cadena Android completa, se actualiza `google_mobile_ads` a 7.0.0 y el mínimo de Dart a 3.9.0, manteniendo la API de publicidad existente.

La decisión se valida mediante `flutter analyze`, `flutter test` y la compilación `flutter build apk --debug`. La firma de producción y la configuración nativa de AdMob siguen fuera del alcance de esta build de pruebas.
