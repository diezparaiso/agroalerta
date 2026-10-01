# SIGPAC: configuración e importación de recintos

AgroAlerta incorpora un adaptador WFS configurable para consultar recintos SIGPAC reales y devolver sus geometrías en GeoJSON. No contiene geometrías ficticias ni presupone que un endpoint o nombre de capa concreto sea oficial.

## Configuración

Configura en el entorno de despliegue el endpoint WFS oficial que corresponda al servicio SIGPAC validado y su nombre de capa:

- `SIGPAC_WFS_URL`: URL base del endpoint WFS (no una URL de visualización WMS).
- `SIGPAC_WFS_TYPENAME`: nombre publicado de la capa de recintos.
- `SIGPAC_WFS_VERSION`: opcional; por defecto `2.0.0`.

Antes de producción, verifica con el proveedor oficial que el endpoint permite WFS GetFeature, el formato GeoJSON, el CRS solicitado y la cobertura territorial. Si el servicio publica WFS 1.1.0 u otro formato/CRS, adapta la configuración/serialización y añade pruebas contra ese contrato real. No se han incorporado credenciales ni se declara conectividad real hasta configurar y verificar el endpoint.

## API

- `GET /api/v1/sigpac/health`: informa si el endpoint y la capa están configurados. No prueba por sí solo que el proveedor esté disponible.
- `GET /api/v1/sigpac/recintos?bbox=-6.1,37.2,-5.8,37.5&limit=100`: consulta por extensión geográfica WGS84 y devuelve GeoJSON FeatureCollection con polígonos y atributos originales.
- `POST /api/v1/sigpac/importar` con JSON `{"bbox":"-6.1,37.2,-5.8,37.5","limit":100}`: consulta y guarda los recintos en SQLite por usuario, actualizando los ya importados en lugar de duplicarlos.
- `GET /api/v1/sigpac/importados?limit=100&offset=0`: devuelve los recintos importados como GeoJSON, incluyendo su geometría y propiedades originales.

Respuestas:
- `503`: proveedor sin configurar.
- `422`: bbox inválida.
- `502`: error del proveedor o respuesta no GeoJSON.
- `504`: timeout.

La búsqueda por provincia/municipio/polígono/parcela y la asociación con una explotación/campaña siguen pendientes hasta validar los nombres y formatos de campos del servicio oficial concreto. La importación persistente por bbox está implementada; no se debe considerar verificada en producción hasta probar el endpoint oficial real.
