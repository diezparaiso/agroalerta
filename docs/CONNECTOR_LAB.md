# Laboratorio temporal de conectores

Pantalla Flutter provisional para comprobar las respuestas de RIA-IFAPA y AEMET, identificar los campos originales y exportar un libro XLSX con tres hojas: datos originales, datos interpretados y metadatos de consulta.

## Estado de cada integración

- **RIA-IFAPA:** cliente HTTP sin API key. El laboratorio consulta el catálogo real de estaciones mediante `GET /estaciones`. El cliente también contiene el método de datos diarios `/datosdiarios/forceEt0/{provincia}/{estacion}/{desde}/{hasta}`, que queda disponible para ampliar la prueba por estación.
- **AEMET OpenData:** cliente implementado para predicción diaria municipal. Requiere `AEMET_API_KEY` en el backend. La documentación oficial confirma que el endpoint exige autenticación por cabecera `api_key` y devuelve la URL de datos en dos pasos. La clave no debe incluirse en Flutter, APK, respuestas JSON ni logs.
- **MAPA:** existe importación de catálogo en el proyecto, pero no un conector de consulta directa en esta rama; se muestra como no implementado.
- **SIGPAC:** no se ha encontrado un cliente SIGPAC real conectado en esta rama; se muestra como no implementado.

## Uso

Desde Ajustes, abrir Laboratorio de conectores y pulsar Probar. Para AEMET se utiliza el código INE de municipio (por defecto, `41091`, Sevilla). La respuesta JSON original se conserva en pantalla; se muestran los nombres de campos de los primeros registros y se exportan todos los registros disponibles al libro Excel. El botón superior copia las respuestas completas en JSON.

Solo el estado `connected` significa que una consulta devolvió datos en esa ejecución. `not_configured` significa que falta la clave; no equivale a un error de la API. Las pruebas automatizadas simulan la respuesta AEMET y verifican que la clave no se devuelve al cliente: no sustituyen una petición real con credenciales.

## Configuración pendiente

Definir `AEMET_API_KEY` como variable de entorno o secreto del servicio backend y reiniciar/re desplegar ese servicio por el procedimiento habitual. No guardar la clave en el repositorio ni en configuración Flutter. Después, ejecutar la prueba AEMET desde la pantalla y guardar el XLSX original como evidencia de la respuesta.

La pantalla es temporal y se podrá retirar cuando se cierre la auditoría de conectores. No constituye todavía un diseño de base de datos ni un contrato definitivo para los datos externos.

## Referencias oficiales

- AEMET OpenData: https://opendata.aemet.es/dist/
- Solicitud y características de API Key: https://opendata.aemet.es/centrodedescargas/info
- IFAPA, Red de Información Agroclimática de Andalucía: https://www.juntadeandalucia.es/agriculturaypesca/ifapa/web/red-de-informacion-agroclimatica-de-andalucia
