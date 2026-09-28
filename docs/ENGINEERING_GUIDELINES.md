# Guía de ingeniería de AgroAlerta

## Regla principal
Todo cambio técnico relevante debe quedar documentado en el repositorio junto con su implementación y validación. El repositorio es la memoria técnica del proyecto.

## Principios
- Separar adquisición de datos, dominio agronómico, persistencia y presentación.
- No inventar datos agrícolas ni meteorológicos para producción. Si no hay evidencia actual, expresarlo explícitamente.
- Mantener trazabilidad entre fuente, fecha de observación, contexto meteorológico, cálculo de riesgo y alerta.
- Las alertas son eventos persistidos; los endpoints de consulta no deben recalcular ni crear alertas.
- Diseñar operaciones de ingesta y sincronización para ser idempotentes.
- No usar evidencia obsoleta como si fuera actual.
- Aplicar aislamiento por propietario en parcelas, telemetría, riesgos, alertas y tokens.
- Priorizar fuentes oficiales y documentar sus contratos y limitaciones.
- Configurar URLs, credenciales y límites mediante entorno, nunca con secretos o supuestos ocultos en código.
- Añadir o actualizar pruebas cuando cambie el comportamiento.
- Validar mediante CI cuando el entorno local no esté disponible.

## Definición de terminado
Un cambio técnico no se considera terminado hasta que, cuando corresponda, incluye: implementación, pruebas, documentación, configuración reproducible y validación CI. Si existe un bloqueo externo, debe quedar documentado con su causa.

## Registro de decisiones
Las decisiones arquitectónicas y de comportamiento se registran en `docs/DECISIONS.md`. Para cada decisión relevante se documentan contexto, decisión, consecuencias y validación.


## Persistencia y esquema
- El esquema de base de datos debe inicializarse desde un único punto de bootstrap; los métodos de escritura no deben crear tablas durante operaciones normales.
- Toda modificación estructural nueva debe introducir una versión de esquema y una prueba de migración o compatibilidad.
- La configuración del motor de persistencia debe ser explícita. No se debe anunciar soporte para un motor hasta disponer de un adaptador probado.
