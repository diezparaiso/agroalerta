# SIGPAC HubCloud: consulta e importación de recintos

AgroAlerta consulta el servicio público OGC API – Features de SIGPAC HubCloud. La colección por defecto es `recintos`; la geometría GeoJSON y los atributos originales se guardan en SQLite.

## Proveedor y configuración

- Base URL predeterminada: `https://sigpac-hubcloud.es/ogcapi`
- Colección predeterminada: `recintos`
- `SIGPAC_OGC_API_URL`: opcional, permite cambiar la base URL.
- `SIGPAC_OGC_COLLECTION`: opcional, por defecto `recintos`.
- `AGROALERTA_DB_PATH`: ruta de SQLite, por defecto `backend/agroalerta.db`.

No se requiere API key en las consultas públicas probadas documentalmente; si el proveedor cambia sus condiciones, habrá que adaptar la autenticación. La colección publicada describe los recintos de la campaña en uso, no garantiza un histórico de campañas.

## Endpoints internos de AgroAlerta

- `GET /api/v1/sigpac/health`: comprueba conectividad con la metadata de la colección.
- `GET /api/v1/sigpac/recintos?bbox=-6.1,37.2,-5.8,37.5&limit=100`: solicita recintos dentro de una extensión geográfica WGS84 y devuelve GeoJSON.
- `POST /api/v1/sigpac/importar` con JSON `{"bbox":"-6.1,37.2,-5.8,37.5","limit":100}`: consulta el proveedor y persiste los recintos, incluida geometría y atributos. Repetir la importación actualiza por ID de origen en vez de crear duplicados.
- `GET /api/v1/sigpac/importados?limit=100&offset=0`: devuelve los recintos persistidos como GeoJSON.

La consulta por bbox devuelve una página limitada por `limit`; si el resultado alcanza el límite, el cliente debe reducir el área o implementar paginación para importar zonas extensas. No debe interpretarse una sola petición como descarga completa de una provincia.

## Verificación

- Las pruebas automatizadas simulan el contrato OGC y verifican consulta, validación de bbox, persistencia de polígonos y deduplicación.
- La documentación pública de `/ogcapi/collections?f=json` expone la colección `recintos`.
- La petición de elementos con bbox debe validarse en el entorno de ejecución/CI con acceso HTTP al proveedor antes de declarar completada una importación real. Si la red del entorno no permite consultar el endpoint, se debe informar como no verificada; los tests con respuestas simuladas no sustituyen una prueba de integración real.

Errores principales: `422` bbox inválida, `502` respuesta/error del proveedor y `504` timeout.
