# AgroAlerta — registro técnico y fuente de verdad

> Documento de cierre técnico de la línea de desarrollo agronómico. Describe qué se ha construido, cómo se conecta, qué contratos expone y qué queda explícitamente fuera.

## 1. Alcance

AgroAlerta es una aplicación Flutter + FastAPI orientada a olivar y viñedo. Esta línea de desarrollo ha evolucionado el backend desde un MVP de avisos hacia un **sistema de operación agronómica trazable por parcela y campaña**.

El flujo funcional actual es:

**Parcela → señales agronómicas → riesgo → decisión explicable → campaña → actividades → resultado productivo**

La persistencia de desarrollo continúa siendo SQLite y los contratos HTTP están preparados para una futura migración a PostgreSQL/PostGIS.

## 2. Registro de módulos construidos

### PR #2 — endurecimiento de producción y dashboard
- Aislamiento de datos por propietario en rutas de parcelas, clima, telemetría, enfermedades y avisos.
- Endurecimiento de CORS.
- Eliminación de `backend/agroalerta.db` del control de versiones y actualización de `.gitignore`.
- Actualización de `.env.example`.
- Dashboard conectado a identificadores reales de parcela.
- Base de autenticación preparada para producción.

### PR #3 — motor de riesgo agroclimático
- Telemetría ampliada con `rainfall_mm_24h`.
- Reglas parametrizadas para repilo y mildiu.
- Riesgo calculado a partir de condiciones agronómicas en lugar de una señal fija.
- Pruebas unitarias y de API del motor.

### PR #4 — inteligencia hídrica
- Nuevo contrato de inteligencia de riego por parcela.
- Endpoint `GET /api/v1/parcels/{parcel_id}/irrigation/intelligence?window_days=7`.
- Integración de humedad/telemetría y contexto temporal para apoyar decisiones de riego.
- Pruebas del módulo.

### PR #5 — decisión agronómica explicable
- Nuevo motor `agronomic_decision`.
- Combina riesgo, telemetría, clima, reportes de campo y señal regional cuando están disponibles.
- Devuelve puntuación, prioridad, confianza, explicación, evidencias y siguientes pasos.
- No prescribe productos ni dosis.
- Endpoint `GET /api/v1/agronomic-decision/{parcel_id}/{disease_code}`.

### PR #6 — centro de explotación
- Nuevo centro operativo de finca.
- Resumen de parcelas, sensores, telemetría y riesgos.
- Eventos recientes ordenados temporalmente.
- Endpoint `GET /api/v1/farm/center`.
- Persistencia de snapshots de riesgo para análisis operativo.

### PR #7 — línea temporal agronómica
- Nuevo tipo de actividad manual: trabajo, riego, tratamiento, observación y cosecha.
- Persistencia de `agronomic_activities`.
- Timeline que combina actividad manual, riesgo y telemetría.
- Endpoints:
  - `POST /api/v1/parcels/{parcel_id}/activities`
  - `GET /api/v1/parcels/{parcel_id}/activity-timeline`

### PR #8 — campañas agrícolas
- Nuevo ciclo de campaña con cultivo, temporada, variedad, objetivo productivo, notas y estado.
- Estados: `planned`, `active`, `closed`, `cancelled`.
- Regla de una única campaña activa por parcela.
- Validación de cultivo y fechas.
- Resumen de actividades, riego, tratamientos, observaciones, cosechas y riesgo.
- Persistencia de `crop_campaigns`.
- Endpoints:
  - `POST /api/v1/parcels/{parcel_id}/campaigns`
  - `GET /api/v1/parcels/{parcel_id}/campaigns`
  - `PATCH /api/v1/campaigns/{campaign_id}/status`
  - `GET /api/v1/campaigns/{campaign_id}/summary`

### PR #9 — conexión campaña ↔ decisión
- Persistencia de decisiones asociadas a campaña en `campaign_decisions`.
- Validación de que campaña y parcela coinciden y pertenecen al propietario.
- Consulta de decisiones por campaña.
- Endpoint `GET /api/v1/campaigns/{campaign_id}/decisions`.
- La decisión conserva código de enfermedad, puntuación, prioridad y titular.
- La integración permite que la campaña sea el contexto longitudinal de las decisiones.

### PR #12 — módulos Flutter de explotación y campañas
- Se completa la exposición en Flutter del centro de explotación ya existente en backend.
- Se añade gestión de campañas por parcela usando los contratos ya definidos.
- Se permite alta y cambio de estado de campañas desde la interfaz.
- Se muestra el resumen de resultados productivos ya calculado por backend.
- No se añade ningún nuevo concepto de dominio ni persistencia.

### PR #10 — ciclo de resultados productivos
- Persistencia de resultados de cosecha en `campaign_results`.
- Registro de fecha, kg cosechados, hectáreas productivas, kg comercializables, calidad, destino y notas.
- Cálculo automático de rendimiento `kg/ha`.
- Conversión del objetivo de campaña `t/ha → kg/ha`.
- Cálculo de desviación porcentual respecto al objetivo.
- Resumen productivo que enlaza producción con actividades, tratamientos, riegos y decisiones.
- Endpoints:
  - `POST /api/v1/campaigns/{campaign_id}/results`
  - `GET /api/v1/campaigns/{campaign_id}/results`
  - `GET /api/v1/campaigns/{campaign_id}/results/summary`

## 3. Modelo funcional consolidado

### Parcela
Es la unidad espacial y de propiedad. Todo dato operativo debe quedar vinculado a una parcela y, cuando corresponda, a su propietario.

### Riesgo
Es una señal calculada sobre enfermedades/cultivos. Incluye puntuación, nivel y confianza.

### Decisión
Es una interpretación explicable del riesgo y otras evidencias. No equivale a una prescripción fitosanitaria.

### Campaña
Es la unidad temporal de gestión agronómica. Agrupa una temporada/cultivo concreto de una parcela.

### Actividad
Es el registro operativo de lo que se hizo u observó en campo.

### Resultado
Es la salida productiva de la campaña. Permite medir el rendimiento real frente al objetivo.

## 4. Persistencia

Las principales tablas incorporadas o ampliadas en esta línea son:

- `agronomic_activities`
- `crop_campaigns`
- `campaign_decisions`
- `campaign_results`

La capa `storage` concentra la creación de tablas y operaciones CRUD/listado. Los módulos `domain` calculan reglas y agregaciones; `main.py` expone los contratos HTTP.

## 5. Reglas importantes

### Campañas
- La parcela de la URL y la parcela del payload deben coincidir.
- El cultivo de la campaña debe coincidir con el cultivo de la parcela.
- `ended_at` no puede ser anterior a `started_at`.
- No puede existir más de una campaña activa por parcela.
- Al cerrar una campaña se puede completar automáticamente su fecha de finalización.

### Resultados
- El resultado debe pertenecer a la campaña indicada.
- La fecha de cosecha no puede ser anterior al inicio.
- Si la campaña tiene fecha final, la cosecha no puede quedar fuera del periodo.
- `harvested_quantity_kg > 0`.
- `productive_area_ha > 0`.
- Rendimiento = `harvested_quantity_kg / productive_area_ha`.
- Objetivo = `target_yield_t_ha * 1000`.
- Desviación = `(rendimiento - objetivo) / objetivo * 100`, cuando existe objetivo positivo.

## 6. Trazabilidad

Una campaña puede reconstruirse temporalmente con:

1. Actividades realizadas.
2. Telemetría disponible.
3. Riesgos detectados.
4. Decisiones generadas.
5. Riegos y tratamientos registrados como actividades.
6. Cosechas/resultados.
7. Rendimiento final frente al objetivo.

Esto permite pasar de un sistema de avisos aislados a un historial de explotación.

## 7. API de referencia

| Área | Método | Ruta |
|---|---|---|
| Riesgo | GET | `/api/v1/disease-risk/{parcel_id}` |
| Decisión | GET | `/api/v1/agronomic-decision/{parcel_id}/{disease_code}` |
| Centro finca | GET | `/api/v1/farm/center` |
| Actividad | POST | `/api/v1/parcels/{parcel_id}/activities` |
| Timeline | GET | `/api/v1/parcels/{parcel_id}/activity-timeline` |
| Campaña | POST | `/api/v1/parcels/{parcel_id}/campaigns` |
| Campañas | GET | `/api/v1/parcels/{parcel_id}/campaigns` |
| Estado campaña | PATCH | `/api/v1/campaigns/{campaign_id}/status` |
| Resumen campaña | GET | `/api/v1/campaigns/{campaign_id}/summary` |
| Decisiones | GET | `/api/v1/campaigns/{campaign_id}/decisions` |
| Resultado | POST | `/api/v1/campaigns/{campaign_id}/results` |
| Resultados | GET | `/api/v1/campaigns/{campaign_id}/results` |
| Resumen resultados | GET | `/api/v1/campaigns/{campaign_id}/results/summary` |
| Inteligencia hídrica | GET | `/api/v1/parcels/{parcel_id}/irrigation/intelligence?window_days=7` |

## 8. Calidad y pruebas

Se han añadido pruebas específicas para:
- riesgo agroclimático;
- decisiones agronómicas;
- centro de explotación;
- timeline de actividad;
- gestión de campañas;
- conexión campaña/decisión;
- cálculo y agregación de resultados productivos.

Los comandos documentados para ejecutar la suite backend son:

```bash
PYTHONPATH=backend python -m pytest backend/tests -q
```

**Estado de verificación:** esta documentación registra los tests implementados, pero no afirma una ejecución de CI en este cierre porque no se ha verificado aquí el resultado de GitHub Actions.

## 9. Estado de integración

La línea actual es `feature/campaign-results`, basada en `feature/campaign-decision-flow`.

PR asociado:
- PR #10 — Cerrar ciclo de resultados productivos de campañas.

La serie anterior permanece como historial de desarrollo:
- PR #1 — capa de datos agronómicos reales.
- PR #2 — endurecimiento y dashboard.
- PR #3 — motor de riesgo.
- PR #4 — inteligencia hídrica.
- PR #5 — decisión agronómica.
- PR #6 — centro de explotación.
- PR #7 — timeline.
- PR #8 — campañas.
- PR #9 — decisiones en campañas.
- PR #10 — resultados productivos.
- PR #12 — módulos Flutter de explotación y campañas.

No se debe interpretar que un PR abierto está integrado en `main` hasta que GitHub confirme su merge.

## 10. Límites conocidos

- SQLite sigue siendo el almacenamiento de desarrollo.
- Los conectores externos agronómicos/metereológicos requieren configuración y validación productiva.
- Los resultados productivos son datos introducidos por el operador; el sistema no inventa kilos ni superficie.
- Las decisiones agronómicas son de apoyo y trazabilidad, no sustituyen etiqueta oficial ni asesoramiento técnico.
- El registro de tratamiento actualmente aprovecha la actividad agronómica; una trazabilidad normativa completa de producto, materia activa, dosis y plazo de seguridad requiere un módulo específico de tratamientos.

## 11. Criterio de cierre de esta etapa

Esta etapa se considera **documentalmente cerrada** cuando:
- cada módulo tiene una responsabilidad definida;
- los contratos HTTP están enumerados;
- las tablas nuevas están registradas;
- las reglas de negocio están escritas;
- las pruebas existentes están identificadas;
- los PR que originaron la evolución están enlazados por número;
- no se presenta como integrado aquello que GitHub aún no haya fusionado.

La siguiente ampliación funcional natural, si se decide continuar, es separar la trazabilidad de tratamientos de la actividad genérica y añadir costes/ingresos para completar el resultado económico de campaña.
