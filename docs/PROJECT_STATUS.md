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
| Parcelas | 70% |
| Meteorología RIA / AEMET | 65% |
| Motor agronómico y riesgo | 70% |
| Alertas | 75% |
| Notificaciones FCM | 75% |
| IoT / telemetría | 75% |
| Informes de campo | 72% |
| Productos fitosanitarios / MAPA | 35% |
| GIS / contexto espacial | 45% |
| Flutter / UI-UX | 78% |
| Offline / sincronización | 65% |
| Privacidad / publicidad | 75% |
| Tests / QA / CI | 65% |
| Despliegue / producción | 45% |

**Estimación global de desarrollo funcional: ~68%.**

La estimación global es ponderada por importancia funcional de cada módulo; por tanto, no equivale a la media aritmética de la tabla.

**Preparación para producción: ~45–50%.** El principal desfase procede de integraciones externas aún no completamente verificadas, configuración de servicios productivos, observabilidad, despliegue y cobertura de pruebas.

## Qué está incluido en cada porcentaje

### 1. Backend / API — 90%

Implementado: FastAPI, persistencia SQLite, endpoints de parcelas, clima, riesgo, alertas, informes y fuentes de datos, separación de dominio y conectores.

Implementado: endurecimiento de concurrencia SQLite (WAL, busy timeout y foreign keys). Pendiente: migración/operación PostgreSQL/PostGIS, observabilidad completa y validación de carga.

### 2. Autenticación y seguridad — 70%

Implementado: Firebase Auth en cliente y comprobaciones de propietario en recursos sensibles del backend.

Pendiente: revisión integral de autorización, gestión de secretos, endurecimiento de producción y pruebas de seguridad.

### 3. Parcelas — 70%

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

### 8. IoT / telemetría — 75%

Implementado: recepción y uso de telemetría en el dominio de riesgo.

Pendiente: robustez de dispositivos, ingestión real continua, validación de calidad y monitorización.

### 9. Informes de campo — 60%

Implementado: persistencia y CRUD local/backend, fotografías, cola offline y sincronización al recuperar conectividad. Los informes usan las coordenadas reales de la parcela, el sincronizador evita ejecuciones concurrentes y el formulario exige seleccionar explícitamente la parcela antes de registrar la observación.

Pendiente: estado de sincronización visible, reintentos con backoff y explotación agronómica de los informes.

### 10. Productos fitosanitarios / MAPA — 25%

Existe el conector CSV versionado y ahora el API/cliente no presentan productos ficticios: solo exponen un snapshot configurado mediante `MAPA_CATALOG_PATH`. Pendiente: automatizar/verificar la obtención del registro oficial vigente, persistencia/actualización del catálogo y explotación segura en recomendaciones.

### 11. GIS / contexto espacial — 45%

Existe base geográfica en parcelas y selección meteorológica por distancia.

Pendiente: SIGPAC/IDEAndalucía, geometrías de parcelas, capas espaciales y análisis territorial.

### 12. Flutter / UI-UX — 78%

Implementado: navegación, dashboard, parcelas, alertas, detalle, historial, autenticación y estados de disponibilidad.

Pendiente: pulido de UX, estados offline avanzados, accesibilidad, integración completa de notificaciones y pruebas de widgets/pantallas.

### 13. Offline / sincronización — 65%

Existe almacenamiento local para parcelas y otros datos.

Pendiente: estrategia completa de sincronización, conflictos, reintentos y consistencia entre dispositivo y servidor.

### 14. Privacidad / publicidad — 75%

Publicidad separada de las pantallas de enfermedad y configuración mediante IDs de prueba.

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
