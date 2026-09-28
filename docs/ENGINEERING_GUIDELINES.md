# Guía de ingeniería de AgroAlerta

## Objetivo

Este documento establece las prácticas obligatorias para evolucionar AgroAlerta como software agrícola mantenible, trazable y seguro.

## Reglas

1. **Cada cambio técnico debe quedar documentado.** Un cambio que afecte arquitectura, datos, integraciones, riesgo, alertas, seguridad, UX o despliegue debe registrar qué se cambió, por qué, impacto y validación.
2. **Separar datos, dominio y presentación.** Los conectores externos no deben contener reglas agronómicas. La normalización ocurre en la capa de datos/evidencia; el cálculo de riesgo permanece en dominio; FastAPI expone contratos; Flutter presenta el resultado.
3. **No inventar datos agronómicos.** Si una fuente real no está disponible, el sistema debe expresar ausencia, antigüedad o baja confianza.
4. **Trazabilidad de cada riesgo.** Un riesgo debe poder relacionarse con parcela, enfermedad, momento de cálculo y evidencia utilizada.
5. **Alertas como eventos persistidos.** Consultar alertas no debe recalcular riesgo ni crear eventos.
6. **Idempotencia.** Ingesta, recalculo y notificación deben poder repetirse sin duplicados ni efectos secundarios indebidos.
7. **No recalcular con evidencia obsoleta sin declararlo.** Una observación fuera de la ventana de frescura no debe tratarse como actual.
8. **Seguridad por propietario.** Toda lectura o escritura de datos privados debe estar limitada al propietario autenticado.
9. **Fuentes oficiales primero.** Cada fuente debe documentar procedencia, contrato, frecuencia y limitaciones.
10. **Pruebas antes de refactorizar.** Cada comportamiento nuevo debe incorporar o actualizar una prueba automatizada.
11. **Configuración por entorno.** URLs, credenciales e identificadores operativos van por configuración/secretos.
12. **Observabilidad.** Los jobs deben distinguir procesado, omitido por datos no frescos, error de fuente y notificación enviada/no enviada.
13. **Contratos estables.** Un cambio de API debe actualizar backend, cliente y pruebas en el mismo cambio.
14. **Documentar decisiones.** Las alternativas relevantes y sus motivos quedan registradas en `docs/DECISIONS.md`.

## Criterio de terminado

Un cambio está terminado cuando está implementado, probado, documentado, no introduce datos ficticios en producción, y CI valida el cambio o deja registrado el bloqueo.
