# SIGPAC HubCloud: consulta e importación de recintos

AgroAlerta consulta el servicio público OGC API – Features de SIGPAC HubCloud. La colección por defecto es `recintos`; la geometría GeoJSON y los atributos originales se guardan en SQLite.

## Autoría y registro de cambios

**Implementación realizada por ChatGPT (OpenAI), a petición del responsable del proyecto AgroAlerta, el 1 de octubre de 2026.** Los cambios de esta fase están en la rama `feature/sigpac-parcel-import` y en el PR [#14](https://github.com/diezparaiso/agroalerta/pull/14). Esta nota identifica la contribución asistida por IA; no significa que la integración esté validada en producción.

- Adaptado el cliente de SIGPAC desde WFS genérico a OGC API – Features de HubCloud.
- Añadidas consulta espacial GeoJSON, persistencia SQLite, deduplicación y pruebas automatizadas.
- Se documentan por separado las pruebas simuladas y las comprobaciones en vivo para no confundirlas.

## Proveedor y configuración

- Base URL predeterminada: `https://sigpac-hubcloud.es/ogcapi`
- Colección predeterminada: `recintos`
- `SIGPAC_OGC_API_URL`: opcional, permite cambiar la base URL.
- `SIGPAC_OGC_COLLECTION`: opcional, por defecto `recintos`.
- `AGROALERTA_DB_PATH`: ruta de SQLite, por defecto `backend/agroalerta.db`.

La consulta del catálogo público confirma la colección `recintos`, descrita como los recintos SIGPAC de la campaña en uso. No garantiza un histórico de campañas. No se ha establecido que haga falta API key para estas consultas públicas.

## Endpoints internos de AgroAlerta

- `GET /api/v1/sigpac/health`: comprueba conectividad con la metadata de la colección.
- `GET /api/v1/sigpac/recintos?bbox=-6.1,37.2,-5.8,37.5&limit=100`: solicita recintos dentro de una extensión geográfica y devuelve GeoJSON.
- `POST /api/v1/sigpac/importar` con JSON `{"bbox":"-6.1,37.2,-5.8,37.5","limit":100}`: consulta el proveedor y persiste los recintos, incluida geometría y atributos. Repetir la importación actualiza por ID de origen en vez de crear duplicados.
- `GET /api/v1/sigpac/importados?limit=100&offset=0`: devuelve los recintos persistidos como GeoJSON.

La consulta por bbox devuelve una página limitada por `limit`; si el resultado alcanza el límite, el cliente debe reducir el área o implementar paginación para importar zonas extensas. No debe interpretarse una sola petición como descarga completa de una provincia.

## Verificación (1 de octubre de 2026)

- **Verificado en vivo:** la ruta `/ogcapi/collections?f=json` respondió con JSON y publicó la colección `recintos`, sus enlaces `items`, el alcance espacial y los CRS admitidos. Esto confirma el catálogo y los metadatos, no la descarga de geometrías.
- **No verificado en vivo:** no he conseguido obtener una respuesta utilizable de `/ogcapi/collections/recintos/items` con un bbox desde la herramienta de navegación disponible. Por ello, no afirmo que ya se haya importado un recinto real.
- **Verificado en CI:** el trabajo backend del commit `c3b262085746c961d8db02987b83738e9d7537cc` terminó correctamente ejecutando `PYTHONPATH=backend python -m pytest backend/tests -q`. Las pruebas del conector usan respuestas simuladas, por lo que no sustituyen la consulta real.
- **CI global:** el trabajo backend pasó, pero el trabajo Flutter falló en `flutter analyze` por errores de sintaxis/tipos en pantallas existentes (`home_screen.dart`, `parcels_screen.dart`, `products_screen.dart` y `settings_screen.dart`). Es un fallo separado de la suite backend SIGPAC.

## Siguiente comprobación necesaria

Ejecutar desde un entorno con salida HTTPS al proveedor una petición real, por ejemplo `GET https://sigpac-hubcloud.es/ogcapi/collections/recintos/items?f=json&bbox=-6.1,37.2,-5.8,37.5&limit=3`, verificar que devuelve una FeatureCollection con al menos una geometría y después probar `POST /api/v1/sigpac/importar` y consultar `/api/v1/sigpac/importados`. Hasta completar ese paso, la importación de datos reales se considera pendiente.

Errores principales: `422` bbox inválida, `502` respuesta/error del proveedor y `504` timeout.


## Etapa SIGPAC visual — rama `feature/sigpac-map-selection` (1 de octubre de 2026)

**Autoría:** cambios implementados por ChatGPT (OpenAI) a petición del responsable del proyecto.

### Cambios de esta etapa
- Añadida prueba de widget inicial en `test/features/parcels/sigpac_map_screen_test.dart` para verificar controles y campos de búsqueda (creada, aún no ejecutada).
- Añadida pantalla Flutter `SigpacMapScreen` en la carpeta existente `lib/src/features/parcels/`, con búsqueda por bbox, visualización de anillos exteriores de Polygon y MultiPolygon, selección para inspección y lista de atributos.
- Añadida ruta `/parcels/sigpac` en GoRouter y acceso desde la pantalla de parcelas.
- Añadidos métodos SIGPAC a `ApiClient`; Flutter llama únicamente a la API de AgroAlerta, no al proveedor externo directamente.
- La acción de importar utiliza el contrato ya existente `POST /api/v1/sigpac/importar` y comunica que importa el área, no solo la selección.
- La consulta usa un máximo de 100 resultados en la interfaz para evitar presentar una consulta parcial como descarga completa.

### Contratos utilizados
- `GET /api/v1/sigpac/recintos?bbox=oeste,sur,este,norte&limit=100` devuelve una FeatureCollection GeoJSON.
- `POST /api/v1/sigpac/importar` recibe `{"bbox":"oeste,sur,este,norte","limit":100}`.
- Se conserva `GET /api/v1/sigpac/importados?limit=100&offset=0` en el cliente API para el siguiente paso de asociación y consulta de los recintos guardados.

### Verificación y límites
- **Implementado en código:** pantalla, ruta, métodos del cliente y enlace desde Parcelas.
- **CI de esta rama (ejecución asociada a un commit anterior a los últimos cambios):** backend completado correctamente; Flutter falla en `flutter analyze` por 22 incidencias. Las incidencias listadas por el analizador están en pantallas existentes (alertas, inicio, parcelas, productos, ajustes, dispositivos e informes); la pantalla SIGPAC solo tenía un import sin uso, eliminado en un commit posterior. `flutter test` se omitió porque el análisis falló antes.
- **Pendiente de ejecutar tras el último commit:** `flutter analyze`, prueba de widget, suite Flutter y suite backend en el estado final de la rama. No se afirma que compile ni que pase CI.
- **Pendiente:** validar con una respuesta real del endpoint `items`; probar en móvil/web; dibujar MultiPolygon y huecos; zoom automático a resultados; importar recintos seleccionados individualmente (el contrato actual solo permite importar por bbox); enlazar los recintos importados con la entidad de parcela del agricultor; gestionar paginación completa y límites del proveedor.
- **Limitación de privacidad:** el backend actual utiliza su mecanismo existente de token opcional; revisar la autorización y el aislamiento por usuario antes de usar la importación con datos de producción.
