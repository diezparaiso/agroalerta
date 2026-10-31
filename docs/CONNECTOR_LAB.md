# Laboratorio temporal de conectores

Pantalla Flutter accesible desde **Ajustes → Laboratorio de conectores**. Permite consultar las respuestas originales de RIA-IFAPA y AEMET y exportar un XLSX de tres hojas: Datos originales, Datos interpretados e Información de consulta.

## Conectores

- **RIA-IFAPA:** consulta el catálogo de estaciones mediante `GET {RIA_BASE_URL}/estaciones`; también incluye consulta de datos diarios por estación. No requiere API key.
- **AEMET OpenData:** predicción diaria municipal en dos pasos. Requiere `AEMET_API_KEY` en el backend. Nunca se envía la clave a Flutter ni se devuelve en el JSON.
- **MAPA y SIGPAC:** aparecen como pendientes; no se simula conectividad.

## Prueba

En la pantalla, pulsa **Probar** en RIA. Para AEMET se usa el código INE municipal, por defecto `41091` (Sevilla). Solo el estado `connected` indica que esa ejecución recibió datos. `not_configured` indica que falta la clave; no significa que la API haya fallado.

## Configuración AEMET

Definir `AEMET_API_KEY` como secreto/variable de entorno del servicio backend. No incluirla en el repositorio, Flutter, APK, ni logs. Tras configurarla, reiniciar o desplegar el backend y repetir la prueba.

Las pruebas automáticas usan respuestas simuladas y no sustituyen una consulta real con credenciales.

## CI

La CI ejecuta tests backend, análisis y tests Flutter, además de compilar Flutter Web en release y APK Android en debug.

## Referencias

- AEMET OpenData: https://opendata.aemet.es/dist/
- IFAPA RIA: https://www.juntadeandalucia.es/agriculturaypesca/ifapa/web/red-de-informacion-agroclimatica-de-andalucia
