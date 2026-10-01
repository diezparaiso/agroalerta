# Arquitectura de consultas externas, caché y carga progresiva

**Estado:** diseño aceptado para evolución incremental; no implica que todas las capas estén implementadas.  
**Fecha de revisión:** 1 de octubre de 2026.  
**Ámbito:** Flutter, API FastAPI, conectores externos y futuras tareas de ingesta de AgroAlerta Andalucía.

## 1. Objetivo y problema

AgroAlerta consulta o prevé consultar múltiples fuentes con latencias, límites, formatos, disponibilidad y cadencias distintas: meteorología, reanálisis Copernicus CDS/ERA5, estaciones RIA/IFAPA, SIGPAC y fuentes de productos fitosanitarios. Una pantalla no debe esperar a que todas las fuentes respondan para permitir navegar, ni una caída de una fuente debe convertir datos inexistentes en valores ficticios.

El objetivo arquitectónico es mantener una experiencia interactiva, reducir llamadas redundantes, controlar consumo y concurrencia, comunicar la procedencia y antigüedad de los datos, y permitir evolucionar desde el MVP a varios procesos/instancias sin acoplar la interfaz a cada proveedor.

## 2. Estado real frente al diseño objetivo

### Implementado parcialmente
- El cliente Flutter consulta la API propia mediante el cliente de red existente; Riverpod representa carga, resultado y error de la consulta meteorológica de la pantalla de inicio.
- La tarjeta meteorológica muestra estado de carga, mensaje de espera, estado sin parcela, error y acción de reintento.
- Se ha eliminado el fallback meteorológico ficticio. Si falla la fuente y no existe caché legible, se propaga el error.
- La caché local de meteorología guarda la respuesta correcta junto a `saved_at` en UTC y puede recuperarla cuando falla la consulta.
- Se registró ADR-007 en `docs/DECISIONS.md`.

### No debe darse por terminado
- La ruta de meteorología por parcela no tiene aún una integración real verificada en vivo y puede devolver 503.
- La caché móvil actual no es compartida entre usuarios/dispositivos y no evita por sí sola llamadas simultáneas al proveedor desde el backend.
- No hay un gestor genérico de trabajos de larga duración, una cola distribuida ni una estrategia de actualización programada común a todos los conectores.
- Los conectores Copernicus y SIAR requieren credenciales/contratos y validación en vivo; las pruebas de entrada/configuración no certifican acceso real.
- La pantalla de inicio conserva otras tarjetas expresamente demostrativas. Deben migrarse por separado, señalando su condición de ejemplo y sin reutilizarlas como información operativa.

## 3. Principios de diseño

1. **Flutter solo llama al backend de AgroAlerta.** Las credenciales de proveedores externos permanecen en el servidor.
2. **Cada fuente falla de forma independiente.** Un fallo de Copernicus no debe ocultar datos válidos de RIA ni impedir ver parcelas.
3. **No bloquear navegación.** El trabajo de red se realiza asíncronamente; la UI muestra estados locales y no espera a un conjunto global de fuentes.
4. **Procedencia explícita.** Toda observación normalizada debe conservar fuente, fecha de observación, fecha de recuperación, unidad, calidad/estado y, cuando aplique, distancia/resolución espacial.
5. **No confundir observación con reanálisis ni estimación con medición.** Por ejemplo, ERA5 es reanálisis y no una lectura instantánea de la parcela.
6. **Caché con caducidad específica de fuente y variable.** No existe un TTL universal adecuado para meteorología, catálogo SIGPAC y registros de productos.
7. **Sin sustituciones silenciosas.** Si se usan datos antiguos, la respuesta y la UI deben identificarlos como antiguos; si no hay datos, mostrar ausencia/error explícitos.
8. **Deduplicar antes de aumentar concurrencia.** Solicitudes idénticas deben compartir trabajo en curso cuando sea seguro.
9. **Límites por proveedor.** Cada conector necesita timeout, límites de fechas/área, concurrencia y tratamiento de respuestas inválidas.
10. **Documentar decisiones y evidencia.** Cada integración nueva actualiza esta guía, ADR, configuración de ejemplo, pruebas y memoria de desarrollo.

## 4. Flujo objetivo de datos

```text
Flutter (Riverpod)
  └─ ApiClient / HTTPS → API FastAPI
       └─ Servicio de aplicación por caso de uso
            ├─ Caché de respuesta normalizada
            ├─ Deduplicación de trabajo en curso
            ├─ Política de timeout / concurrencia / reintento
            └─ Adaptador del proveedor externo
                 └─ API externa
```

La UI no conoce las URLs, autenticación ni el formato nativo de los proveedores. El adaptador transforma la respuesta externa a un esquema interno estable; el servicio añade procedencia, fechas y estado de frescura; la API expone el resultado. Los fallos deben traducirse a errores de dominio/API coherentes sin filtrar secretos ni respuestas sensibles del proveedor.

Para operaciones breves, el endpoint puede responder con el dato o con un error acotado. Para descargas históricas o cálculos largos, se valorará el patrón de trabajo asíncrono: crear trabajo, devolver identificador y estado, consultar progreso/resultado y permitir cancelar si el proveedor y el caso de uso lo permiten. No se debe introducir una cola distribuida hasta que la duración, el volumen o el despliegue lo justifiquen.

## 5. Capas de caché

### 5.1 Caché del cliente
La caché local es una optimización de experiencia offline y tolerancia a fallos. Debe:
- usar claves versionadas y específicas de entidad, por ejemplo `agroalerta.weather.v1.<parcel_id>`;
- guardar respuesta, `saved_at` UTC, y metadatos de fuente cuando existan;
- recuperar únicamente contenido parseable y con forma conocida;
- mostrar claramente que el resultado procede de caché y cuándo se guardó;
- no asumir que SharedPreferences es una base de datos transaccional ni adecuada para grandes series temporales;
- invalidarse o versionarse al cambiar el esquema de respuesta.

La caché local no es una fuente de verdad, no se comparte entre dispositivos y no sustituye al control de acceso del backend. La aplicación debe evitar persistir secretos o datos personales innecesarios.

### 5.2 Caché del backend
Siguiente nivel recomendado: caché compartida en el servicio de aplicación. Inicialmente puede evaluarse una caché TTL en memoria para un despliegue de una sola instancia, con la limitación documentada de que no comparte estado entre procesos y se vacía al reiniciar. Si hay varias réplicas, se necesita un almacén compartido como Redis u otra solución compatible con la infraestructura elegida.

Las claves deben incorporar al menos:
- proveedor/dataset y versión del adaptador;
- parcela o coordenadas normalizadas;
- intervalo temporal solicitado;
- variables, resolución y demás parámetros que alteren el resultado;
- versión de normalización si cambia la semántica de la respuesta.

No incluir tokens ni credenciales en claves o logs. Evitar coordenadas excesivamente precisas en logs de diagnóstico cuando no sean necesarias.

### 5.3 TTL y datos obsoletos
El TTL depende de la semántica de cada fuente y se configura explícitamente por caso de uso. Las condiciones meteorológicas observadas, el reanálisis histórico, los límites SIGPAC y el registro oficial de productos tienen ritmos de cambio distintos. No fijar un TTL global por comodidad.

Hay que distinguir:
- **fresh:** resultado recuperado de fuente/caché dentro de su política de frescura;
- **stale:** dato anterior al TTL, mostrado solo como contingencia si el caso de uso lo permite;
- **unavailable:** no hay dato utilizable;
- **partial:** algunas fuentes respondieron y otras no;
- **pending:** trabajo aún en curso.

Un TTL vencido no implica siempre borrar inmediatamente el dato: puede conservarse para contingencia, pero la respuesta debe etiquetarlo y aplicar una antigüedad máxima de visualización definida por producto. La política exacta para cada variable meteorológica sigue pendiente de decisión y validación.

## 6. Concurrencia, deduplicación y resiliencia

- Configurar timeouts de conexión y lectura; evitar esperas indefinidas.
- Limitar simultaneidad por proveedor y por tipo de consulta para no agotar workers ni exceder cuotas.
- Deduplicar peticiones equivalentes en vuelo mediante una clave estable, compartiendo resultado solo si autorización y ámbito de datos coinciden.
- No reintentar automáticamente errores de validación (4xx) o credenciales. Aplicar reintentos limitados con espera incremental solo a fallos transitorios (timeouts, 429/5xx), respetando `Retry-After` cuando esté disponible.
- Establecer límites a rango de fechas, extensión geográfica, número de elementos y tamaño descargado.
- Aislar operaciones bloqueantes de SDKs de proveedores del event loop de FastAPI, usando ejecución en hilo/proceso según la biblioteca y perfil de consumo.
- Evitar paralelismo ilimitado: usar semáforos o límites por proveedor; revisar los límites reales antes de fijar valores de producción.
- Los fallos parciales se registran por fuente y no deben descartar resultados válidos de otras fuentes.
- Añadir métricas agregadas de latencia, tasa de error, aciertos de caché y cola/concurrencia. Nunca registrar API keys, tokens ni payloads personales completos.

## 7. Contrato de respuesta interno

Las respuestas normalizadas deberían exponer, según aplique:
- `source` y `dataset`;
- `observed_at` (tiempo de observación válido) y `retrieved_at` (momento de consulta/descarga);
- `cache_status`: fresh/stale/miss, o equivalente documentado;
- `data_status`: complete/partial/insufficient/unavailable;
- `units` y variables usadas;
- `quality_flags`, incertidumbre y resolución espacial/temporal;
- datos y errores por fuente sin exponer detalles internos sensibles.

No cambiar los contratos existentes de golpe: introducir campos compatibles, pruebas de contrato y migración de consumidores. Los timestamps se normalizan a UTC internamente y se convierten a hora local solo para presentación.

## 8. Estados y mensajes de interfaz

Cada componente que depende de una API debe distinguir:
- carga inicial;
- actualización en curso con dato previo disponible;
- resultado válido;
- resultado parcial;
- vacío válido (por ejemplo, cero alertas);
- error sin caché;
- dato antiguo de caché con fecha/hora;
- acción de reintento.

Mensajes recomendados, ajustados al contexto:
- «Consultando la fuente… Puedes seguir usando la app».
- «Actualizando datos; se muestran los últimos datos guardados del [fecha/hora]».
- «No hay datos disponibles para este periodo».
- «No se ha podido actualizar. Reintentar».
- «Esta fuente no ha respondido; los datos de las demás fuentes siguen disponibles».

No mostrar spinner permanente sin explicación. El reintento debe volver a ejecutar la consulta correspondiente, no toda la aplicación. Para una actualización de fondo, conservar el dato válido anterior mientras se actualiza y no reemplazarlo por una pantalla vacía sin motivo.

## 9. Integraciones previstas y condiciones de aceptación

### Copernicus CDS / ERA5
- Usar solo desde backend y mantener clave CDS en entorno/secret manager.
- Respetar condiciones del dataset y límites de fechas/área.
- Validar en vivo el contrato de solicitud y unidades con credenciales autorizadas.
- Identificar ERA5 como reanálisis, documentar resolución y píxel seleccionado.
- No conectarlo al motor de riesgo hasta validar normalización, conversión de unidades y pruebas con muestras verificadas.

### RIA/IFAPA
- Mantener catálogo de estaciones, distancia y marcas temporales.
- Verificar contrato real, unidades, códigos de provincia/estación y tratamiento de datos faltantes.
- No inferir continuidad temporal de una única observación.

### SIAR
- Mantener integración desactivada si URL/ruta/autenticación no están confirmadas.
- Tratar respuestas malformadas como error de proveedor; no convertirlas en observaciones vacías válidas.
- Registrar como no verificada hasta completar prueba en vivo autorizada.

### SIGPAC
- Cachear por colección, campaña si existe, filtros y extensión; respetar las condiciones de la fuente.
- No asumir que una consulta espacial parcial es el catálogo completo.
- Mantener trazabilidad entre recinto importado y parcela de negocio.

## 10. Seguridad y privacidad

- Las credenciales externas viven solo en el backend y en el gestor de secretos del despliegue.
- Autorizar cada petición antes de leer cachés de datos privados; la clave de caché y la deduplicación deben incluir el ámbito de propietario cuando corresponda.
- No permitir que un usuario reciba la caché de otra cuenta por colisión de claves.
- Validar parámetros antes de llamar a proveedores y limitar recursos para reducir abuso accidental.
- No incluir coordenadas detalladas, tokens ni respuestas sensibles en logs por defecto.
- Revisar autenticación, retención y eliminación de datos antes de producción.

## 11. Pruebas exigidas para cada nueva fuente

1. Validación de parámetros y límites.
2. Fuente no configurada y credenciales inválidas.
3. Timeout, 429/5xx y error de conexión.
4. JSON/CSV/NetCDF malformado o respuesta vacía.
5. Normalización de unidades, fechas y zona horaria.
6. Caché hit/miss, caducidad, corrupción y contingencia stale.
7. Dos solicitudes iguales concurrentes y comprobación de deduplicación.
8. Fallo parcial de una fuente sin pérdida de las demás.
9. Autorización y aislamiento por usuario/parcela.
10. Prueba de integración en vivo separada, opt-in y con credenciales; registrar resultado, fecha y límites. Los tests simulados no cuentan como validación de conectividad real.

## 12. Plan incremental

1. **Ahora:** mantener los estados de carga/error y la caché meteorológica local sin datos inventados; hacer que la lectura de caché corrupta no oculte el error de red original.
2. **Siguiente:** definir y probar una política de antigüedad meteorológica visible; cubrir UI con tests.
3. **Implementado inicialmente para Copernicus:** caché TTL en proceso y deduplicación en vuelo; se limita a dos recuperaciones simultáneas por proceso. Aún debe ampliarse y validarse antes de aplicarlo a otras fuentes.
4. **Siguiente:** añadir límites por proveedor y métricas básicas.
5. **Más adelante:** trabajos de ingesta programados y cola persistente solo cuando el volumen y el despliegue lo requieran.
6. **Antes de conectar al riesgo:** validar en vivo los contratos y unidades de Copernicus/RIA/SIAR, y usar series temporales verificadas.

## 13. Registro y mantenimiento

Cada desarrollo nuevo debe documentar: problema, alcance, decisión arquitectónica, flujo de datos, configuración, archivos afectados, contratos, límites, seguridad, pruebas, estado de CI, evidencia de conectividad real, deuda técnica y reversión posible. Actualizar también `docs/DECISIONS.md` si se introduce una decisión duradera y `docs/ESTADO_DESARROLLO.md` con el commit y estado real.

ChatGPT de OpenAI ha asistido en la redacción y desarrollo de esta documentación y código a petición del responsable del proyecto. Esta asistencia no implica certificación, titularidad ni garantía por parte de OpenAI o de los proveedores de datos.


## 14. Implementación inicial de caché backend — 1 de octubre de 2026

Se incorpora `backend/app/core/async_cache.py`, una caché asíncrona genérica, acotada por número de entradas y TTL, con deduplicación de solicitudes concurrentes para la misma clave. Los resultados se copian al devolverlos para evitar que un consumidor modifique accidentalmente el objeto almacenado. Los errores del proveedor no se guardan en caché y una cancelación de un consumidor no cancela el trabajo compartido.

Se integra en `GET /api/v1/copernicus/era5/hourly`, `GET /api/v1/ria-ifapa/daily`, `GET /api/v1/ria-ifapa/monthly` y `GET /api/v1/siar/daily`, con políticas separadas por fuente:
- TTL configurado: seis horas.
- Máximo: 128 consultas guardadas por proceso.
- Límite: dos recuperaciones Copernicus simultáneas por proceso.
- La clave incluye coordenadas, fechas, dataset y versión de la consulta; no contiene credenciales.
- El SDK de Copernicus sigue aislando su operación bloqueante con `asyncio.to_thread`.
- Copernicus: TTL de seis horas, máximo 128 entradas y dos recuperaciones concurrentes por proceso.
- RIA/IFAPA: TTL de una hora para agregados diarios y 24 horas para mensuales; máximo 256 entradas por caché y tres recuperaciones simultáneas por proceso.
- SIAR: TTL de una hora, máximo 256 entradas y dos recuperaciones simultáneas por proceso.
- Los errores de proveedor no se guardan como respuestas exitosas; los conectores siguen marcados como no verificados cuando corresponde.

**Limitación de despliegue:** cada worker/proceso mantiene su propia caché y semáforo. No existe coordinación entre réplicas ni persistencia tras reinicio. Antes de desplegar múltiples réplicas o extenderlo a todas las fuentes, se debe evaluar caché compartida y configuración de límites desde entorno.

Pruebas añadidas en `backend/tests/test_async_cache.py`: reutilización de resultado, aislamiento de mutaciones, deduplicación concurrente, no cachear errores y validación de límites. Las políticas de TTL son valores iniciales operativos, pendientes de validación con los ritmos reales de actualización de cada proveedor.


## 15. Aplicación gradual de caché a RIA/IFAPA y SIAR

Se ha extendido la caché a los endpoints diagnósticos RIA/IFAPA diarios y mensuales y al endpoint diario SIAR. Cada clave incorpora fuente/versión, estación, intervalo y parámetros de consulta; se usa SHA-256 para no exponer los parámetros directamente en la clave de almacenamiento. Los límites de concurrencia son por proceso, no globales. Los TTL son iniciales y deben revisarse cuando se confirme la cadencia de actualización y el contrato de cada proveedor. La respuesta cruda sigue sin normalizarse y no se debe utilizar directamente para calcular riesgo.
