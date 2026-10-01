# Integración RIA / IFAPA

**Estado: cliente de agregados diarios y mensuales implementado; conexión real y uso productivo aún pendientes de verificación.**

## Fuente y contrato conocido

La arquitectura de AgroAlerta identifica como base pública:

`https://www.juntadeandalucia.es/agriculturaypesca/ifapa/riaws`

El contrato documentado para agregados diarios es:

`GET /datosdiarios/{provincia}/{estacion}/{anio}/{mesInicio}/{mesFin}`

Para agregados mensuales:

`GET /datosmensuales/{provincia}/{estacion}/{anio}/{mesInicio}/{mesFin}`

No se requiere API key según la especificación del proyecto. La respuesta debe tratarse como dato del proveedor y no se deben asumir campos hasta observar una respuesta real.

## Código

- Cliente: `backend/app/connectors/ria_ifapa_client.py`
- Pruebas: `backend/tests/test_ria_ifapa_client.py`
- Base URL configurable con `RIA_BASE_URL`; valor predeterminado definido en `backend/app/core/config.py`.
- Incluye validación de provincia/estación y rango de meses, soporte de datos diarios y mensuales, timeout HTTP configurable y propagación explícita de errores HTTP.
- Permite inyectar un `httpx.AsyncClient` para pruebas deterministas sin llamadas de red.

## Límite importante: datos horarios

No se considera confirmado el contrato horario de RIA-Web/RIAWS. Por tanto, esta implementación **no inventa un endpoint horario** ni afirma disponer de horas continuas de mojado foliar. Los agregados diarios pueden aportar variables como temperatura, humedad, precipitación y ET₀ según la documentación de referencia, pero no bastan por sí solos para demostrar la duración continua del mojado.

## Pendiente para completar la integración

1. Ejecutar las pruebas del cliente y la suite backend en CI.
2. Hacer una consulta real desde un entorno con acceso HTTPS al servicio y guardar un ejemplo de respuesta anonimizado/no sensible.
3. Confirmar códigos de provincia y estación y el esquema real de los campos.
4. Resolver la estación adecuada para cada parcela y la estrategia de actualización/caché.
5. Diseñar la normalización de observaciones con fecha, unidad, fuente y control de calidad.
6. Investigar y confirmar por separado si existe acceso oficial a datos horarios necesarios para el modelo de mojado foliar.
7. Solo después conectar estas observaciones al motor de riesgo; no convertir agregados diarios en supuestas observaciones horarias.

Las pruebas simuladas validan el contrato que implementa el cliente, no la disponibilidad actual del proveedor ni la corrección agronómica de los datos.
