# Estado del proyecto AgroAlerta

**Fecha de referencia:** 2026-09-28  
**Rama:** `feature/agroalerta-real-data-layer`

## Cómo interpretar estos porcentajes

Los porcentajes son una **estimación de cobertura funcional del alcance previsto del producto**, no una medida de líneas de código ni de esfuerzo restante. Un módulo se considera parcialmente desarrollado cuando existe una parte funcional integrada pero faltan integraciones, pruebas, endurecimiento operativo o funcionalidades previstas.

Se distinguen dos conceptos:

- **Desarrollo funcional:** cuánto del comportamiento previsto está implementado e integrado.
- **Preparación para producción:** cuánto está validado, observable, securizado y operativo con dependencias reales.

La estimación debe actualizarse después de hitos relevantes y no debe interpretarse como una métrica objetiva de calidad.

## Estado global

| Área | Cobertura funcional estimada |
|---|---:|
| Backend / API FastAPI | 90% |
| Autenticación y seguridad | 70% |
| Parcelas | 75% |
| Meteorología RIA / AEMET | 65% |
| Motor agronómico y riesgo | 70% |
| Alertas | 75% |
| Notificaciones FCM | 75% |
| IoT / telemetría | 84% |
| Informes de campo | 72% |
| Productos fitosanitarios / MAPA | 35% |
| GIS / contexto espacial | 45% |
| Flutter / UI-UX | 82% |
| Offline / sincronización | 70% |
| Privacidad / publicidad | 75% |
| Tests / QA / CI | 65% |
| Despliegue / producción | 45% |

**Estimación global de desarrollo funcional: ~69%.**

La estimación global es ponderada por importancia funcional de cada módulo; por tanto, no equivale a la media aritmética de la tabla.

**Preparación para producción: ~45–50%.** El principal desfase procede de integraciones externas aún no completamente verificadas, configuración de servicios productivos, observabilidad, despliegue y cobertura de pruebas.

## Qué está incluido en cada porcentaje

### 1. Backend / API — 90%

Implementado: FastAPI, persistencia SQLite, endpoints de parcelas, clima, riesgo, alertas, informes y fuentes de datos, separación de dominio y conectores.

Implementado: endurecimiento de concurrencia SQLite (WAL, busy timeout y foreign keys). Pendiente: migración/operación PostgreSQL/PostGIS, observabilidad completa y validación de carga.

### 2. Autenticación y seguridad — 70%

Implementado: Firebase Auth en cliente y comprobaciones de propietario en recursos sensibles del backend.

Pendiente: revisión integral de autorización, gestión de secretos, endurecimiento de producción y pruebas de seguridad.

### 3. Parcelas — 75%

Implementado: CRUD, persistencia local, API, asociación por usuario y eliminación de coordenadas ficticias en la interfaz.

Pendiente: GIS completo, edición avanzada, validación geográfica y sincronización robusta de conflictos.

### 4. Meteorología RIA / AEMET — 65%

Implementado: normalización, persistencia de observaciones, catálogo RIA, selección por proximidad, contexto de hasta tres estaciones y ventana de frescura.

Pendiente: verificación completa de contratos externos, operación estable de AEMET/RIA y monitorización de ingestas.

### 5. Motor agronómico / riesgo — 70%

Implementado: cálculo determinista MVP, trazabilidad, niveles de riesgo, contexto meteorológico y telemetría.

Pendiente: ampliar modelos agronómicos, calibración con datos históricos y validación con técnicos/campañas reales.

### 6. Alertas — 75%

Implementado: persistencia de eventos, transiciones de riesgo, deduplicación estable y consulta histórica.

Pendiente: completar pruebas de idempotencia, recuperación, ciclo de vida de notificaciones y experiencia completa de resolución.

### 7. Notificaciones FCM — 75%

Implementado: servicio backend y estructura cliente para tokens/notificaciones.

Pendiente: verificar extremo a extremo permisos, foreground/background, preferencias y despliegue Firebase productivo.

### 8. IoT / telemetría — 82%

Implementado: recepción y uso de telemetría en el dominio de riesgo, histórico temporal 24 h–7 días, selección explícita de parcela y sensor en dashboard, filtro `device_id` en API/SQLite, autorización del sensor por propietario/parcela y rechazo de sensores no registrados o inactivos durante la ingestión.

Pendiente: ingestión real continua, validación de calidad, ciclo de vida completo de dispositivos y monitorización.

### 9. Informes de campo — 72%

Implementado: persistencia y CRUD local/backend, fotografías, cola offline y sincronización al recuperar conectividad. Los informes usan las coordenadas reales de la parcela, el sincronizador evita ejecuciones concurrentes y el formulario exige seleccionar explícitamente la parcela antes de registrar la observación.

Pendiente: estado de sincronización visible, reintentos con backoff y explotación agronómica de los informes.

### 10. Productos fitosanitarios / MAPA — 35%

Existe el conector CSV versionado y ahora el API/cliente no presentan productos ficticios: solo exponen un snapshot configurado mediante `MAPA_CATALOG_PATH`. Pendiente: automatizar/verificar la obtención del registro oficial vigente, persistencia/actualización del catálogo y explotación segura en recomendaciones.

### 11. GIS / contexto espacial — 45%

Existe base geográfica en parcelas y selección meteorológica por distancia.

Pendiente: SIGPAC/IDEAndalucía, geometrías de parcelas, capas espaciales y análisis territorial.

### 12. Flutter / UI-UX — 78%

Implementado: navegación, dashboard, parcelas, alertas, detalle, historial, autenticación y estados de disponibilidad.

Pendiente: pulido de UX, estados offline avanzados, accesibilidad, integración completa de notificaciones y pruebas de widgets/pantallas.

### 13. Offline / sincronización — 65%

Existe almacenamiento local para parcelas y otros datos.

Implementado: cola offline con sincronización sin concurrencia y reintentos por informe con backoff exponencial hasta 1 hora.

Implementado: estado visible de la cola, reintentos por informe con backoff exponencial hasta 1 hora y protección contra sincronizaciones concurrentes.

Implementado: conflictos de edición de parcelas con versión `updated_at`, HTTP 409 y protección en Flutter.

Implementado: reconciliación explícita de versión local/remota con elección del usuario y reintento condicionado por versión.

Pendiente: merge por campos y resolución avanzada de conflictos.

### 14. Privacidad / publicidad — 75%

Publicidad separada de las pantallas de enfermedad y configuración mediante ID de unidad configurable; sin ID configurado, la publicidad permanece desactivada.

Pendiente: configuración productiva, consentimiento cuando corresponda y revisión final de políticas de plataforma.

### 15. Tests / QA / CI — 65%

Backend validado por CI y Flutter con análisis estático. Se han añadido pruebas unitarias de mapeo de parcelas y alertas para impedir regresiones de datos ficticios.

Pendiente: ampliar cobertura de dominio, integración, widgets, notificaciones y pruebas end-to-end.

### 16. Despliegue / producción — 45%

Existe configuración de desarrollo, Docker y CI.

Implementado: ciclo agroclimático explícito y reutilizable con orden catálogo RIA → RAIF → meteorología → riesgo/alertas, preparado para ejecución externa. Pendiente: scheduler productivo, base de datos gestionada, secretos, observabilidad, backups, migraciones y procedimiento de rollback.

## Bloqueadores actuales

1. CI Flutter debe quedar completamente verde con las nuevas pruebas.
2. Hay que automatizar y validar la actualización del catálogo oficial MAPA.
3. Hay que comprobar el flujo de notificaciones foreground/background.
4. Hay que conectar el ciclo agroclimático a un scheduler productivo con control de concurrencia.
5. Las integraciones oficiales externas deben validarse con sus contratos vigentes.
6. El README y documentación histórica deben mantenerse alineados con el estado real.

## Criterio para subir porcentajes

Un módulo no se considerará terminado únicamente porque exista código. Para avanzar hacia 100% debe disponer, según corresponda, de:

- implementación integrada;
- datos reales o contrato externo validado;
- pruebas automatizadas;
- manejo de errores y estados vacíos;
- seguridad y autorización;
- observabilidad;
- documentación de decisiones;
- validación CI;
- preparación operativa para producción.

Este documento es una **fotografía de ingeniería** y debe actualizarse cuando cambie materialmente el alcance o el estado del proyecto.

## Actualización 2026-09-28 — Dashboard visual

La pantalla inicial se ha rediseñado con cabecera contextual, resumen meteorológico, avisos, parcelas, mapa, alertas recientes y sensores, manteniendo adaptación responsive.

También se eliminó el último fallback Flutter que mostraba temperatura, humedad y lluvia sintéticas cuando no había evidencia meteorológica. Ahora el estado se expresa como `No disponible`.

La valoración de Flutter/UI-UX pasa de 78% a 82% por esta mejora integrada. No implica que el módulo esté terminado: siguen pendientes accesibilidad, pruebas de widgets/pantallas, notificaciones completas y validación en dispositivos reales.


## Actualización 2026-09-28 — Idempotencia de informes de campo

Se corrigió el flujo online de observaciones para transmitir el mismo `report_id` que ya se utiliza en la cola offline. La identidad del evento queda ahora conservada en ambos caminos y el backend puede deduplicar reintentos mediante la misma clave persistente.

La cobertura de **Informes de campo** se mantiene en 72% porque este cambio corrige una condición de robustez, pero siguen pendientes la explotación agronómica de los informes y validaciones end-to-end en dispositivo.


## Actualización 2026-09-28 — Cierre funcional del catálogo MAPA

El módulo de productos autorizados deja de ser una lista básica: la API admite filtrado por cultivo/enfermedad y Flutter muestra los metadatos oficiales de dosis y plazo de seguridad disponibles en el snapshot. Se añadió cobertura de mapeo y ausencia explícita de datos.

**Phytosanitarios/MAPA:** 35% → 45%. El siguiente salto dependerá de disponer de un proceso de actualización/validación del catálogo oficial y de integración contextual con el riesgo, sin convertir el catálogo en una recomendación automática de tratamiento.


## Actualización 2026-09-28 — Histórico de telemetría

Se cerró el contrato inicial de histórico reciente de telemetría por parcela: backend autenticado, consulta limitada y ordenada, y cliente Flutter preparado para consumirlo. No se generan valores sintéticos.

**IoT/telemetría:** 75% → 80%. Queda para una fase posterior la visualización temporal avanzada, gestión completa del ciclo de vida del dispositivo y validación con hardware real.


## Actualización 2026-09-28 — Ventanas temporales IoT

El histórico de telemetría ya admite ventanas reales de 24 h hasta 7 días mediante since_hours, con límites de consulta y control de propietario. La visualización avanzada queda preparada para consumir este contrato.
