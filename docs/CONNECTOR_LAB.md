# Laboratorio temporal de conectores

Pantalla Flutter provisional para comprobar las respuestas reales de RIA-IFAPA y AEMET, identificar los campos originales y exportar un libro XLSX con tres hojas: datos originales, datos interpretados y metadatos de consulta.

## Estado conocido en feature/complete-agronomic-workflows

- RIA-IFAPA: cliente HTTP existente; el laboratorio consulta el listado real de estaciones.
- AEMET: cliente existente; requiere `AEMET_API_KEY` y consulta la predicción diaria del código INE indicado.
- MAPA: existe importación de catálogo, pero no un conector de consulta directa; se muestra como no implementado.
- SIGPAC: no se ha encontrado un cliente real en esta rama; se muestra como no implementado.

## Uso

Desde Ajustes, abrir Laboratorio de conectores y pulsar Probar. La respuesta JSON original se conserva en pantalla; se muestran los nombres de campos de los primeros registros y se exportan todos los registros disponibles al libro Excel. El botón superior copia las respuestas completas en JSON.

No se deben interpretar los estados de configuración como prueba de conectividad. Solo `connected` significa que la consulta devolvió datos en esa ejecución. No se guardan claves ni cabeceras de autenticación en las respuestas.

La pantalla es temporal y se podrá retirar cuando se cierre la auditoría de conectores. No constituye todavía un diseño de base de datos ni un contrato definitivo para los datos externos.
