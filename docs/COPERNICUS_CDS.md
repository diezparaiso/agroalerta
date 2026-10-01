# Copernicus Climate Data Store (CDS)

## Implementación inicial

AgroAlerta incorpora un conector para consultar el conjunto ERA5 de niveles de superficie y obtener una serie horaria del píxel más próximo a una coordenada:

- Endpoint: `GET /api/v1/copernicus/era5/hourly?latitude=37.4&longitude=-5.9&start_date=2026-09-01&end_date=2026-09-02`
- Configuración: `COPERNICUS_API_URL` y `COPERNICUS_API_KEY`.
- Dataset solicitado: `reanalysis-era5-single-levels`.
- Variables: temperatura a 2 m, punto de rocío a 2 m, precipitación total y componentes U/V del viento a 10 m.
- Ventana máxima por petición: 7 días. La descarga se realiza en segundo plano para no bloquear el event loop y el fichero temporal se elimina al terminar.
- Unidades originales: temperatura y punto de rocío en kelvin (K), precipitación en metros (m), viento en m/s. Cualquier conversión para mostrar o alimentar indicadores debe ser explícita y probada.
- La respuesta identifica el origen y el conjunto de datos, pero `verified` permanece en `false`; `retrieval_completed` solo indica que la consulta terminó.

## Configuración necesaria

1. Crear/acceder a una cuenta del Climate Data Store.
2. Copiar la clave personal del perfil CDS a `COPERNICUS_API_KEY`.
3. Aceptar las condiciones de uso del dataset en el portal CDS.
4. Verificar el código de solicitud mostrado por el formulario del dataset, porque los campos requeridos pueden cambiar según el producto.

## Limitaciones conocidas

ERA5 es un reanálisis, no una observación en tiempo real ni una medición exacta en la parcela. La implementación descarga un área pequeña alrededor del punto y selecciona el píxel más próximo; la resolución espacial y la representatividad deben mostrarse en la interfaz. No se conecta automáticamente al motor de riesgo hasta validar el contrato de solicitud, los datos reales, las unidades y la estrategia de conversión.

Las pruebas automatizadas de este módulo validan entradas y configuración, no certifican una conexión real con Copernicus. ChatGPT de OpenAI ha asistido en la implementación y documentación; esto no implica certificación por parte de Copernicus o ECMWF.

## Referencias oficiales

- https://cds.climate.copernicus.eu/en/how-to-api
- https://cds.climate.copernicus.eu/api/retrieve/v1/docs
