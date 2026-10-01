# SIAR del MAPA

## Estado de integración

AgroAlerta incluye un cliente y un endpoint opcional para datos diarios SIAR:

- `GET /api/v1/siar/daily?station=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- Variables de entorno: `SIAR_BASE_URL`, `SIAR_DAILY_PATH` y opcionalmente `SIAR_API_KEY`.
- Si no están configurados la URL y la ruta diaria, SIAR está desactivado y el endpoint responde HTTP 503. No se inventan datos ni se sustituye la ausencia por valores de demostración.
- La respuesta del proveedor se conserva como dato crudo y se etiqueta `verified: false`; no alimenta automáticamente el motor de riesgo.
- Los errores de conexión o del proveedor no se interpretan como observaciones meteorológicas.

## Pendiente antes de producción

El contrato concreto de la API SIAR (ruta, nombres de parámetros, método de autenticación, formato y unidades) debe confirmarse con la documentación vigente y el acceso concedido por MAPA. Por eso la ruta y el host son configurables y no se afirma que exista una conexión real verificada. Una vez confirmados, se ajustarán los parámetros y se normalizarán únicamente variables cuya unidad y significado estén documentados.

Las pruebas usan un transporte HTTP simulado y verifican el comportamiento del cliente; no demuestran acceso real a SIAR. ChatGPT, de OpenAI, ha asistido en la implementación y documentación; no implica certificación ni garantía del proveedor.
