# AgroAlerta Andalucía — memoria de desarrollo y estado

**Fecha:** 1 de octubre de 2026  
**Repositorio:** [diezparaiso/agroalerta](https://github.com/diezparaiso/agroalerta)  
**Rama de trabajo:** `feature/sigpac-map-selection`  
**PR relacionado:** [#15](https://github.com/diezparaiso/agroalerta/pull/15)  
**PR SIGPAC:** [#14](https://github.com/diezparaiso/agroalerta/pull/14)

## 1. Quién participa y responsabilidades

- **Responsable del proyecto/producto:** la persona que dirige AgroAlerta Andalucía y solicita los cambios. Su nombre no consta en los datos disponibles, por lo que no se inventa.
- **Asistencia de desarrollo:** ChatGPT, de OpenAI, ha ayudado a redactar documentación y modificar código a petición del responsable del proyecto. Esta atribución no significa que OpenAI sea propietario del producto ni garantice el código.
- **Revisión humana independiente:** no consta una revisión formal completada en esta actualización.
- **Validación agronómica:** pendiente. Los indicadores actuales no son predicciones validadas.
- **Validación técnica:** solo se considera confirmada cuando existe una ejecución comprobable de pruebas o CI. Guardar un commit no demuestra que compile ni que pase las pruebas.

## 2. Resumen del proyecto

AgroAlerta Andalucía es una aplicación Flutter con backend FastAPI orientada a la gestión de parcelas y avisos de riesgo fitosanitario, inicialmente para repilo en olivar y mildiu en viñedo. El alcance de referencia incluye fuentes meteorológicas y agroclimáticas, SIGPAC, consulta de productos del registro MAPA, notificaciones y reportes de campo.

El repositorio contiene una aplicación navegable, API propia, integración SIGPAC en desarrollo y un motor inicial de indicadores. **No debe considerarse todavía un sistema agronómico validado ni un servicio de producción plenamente verificado.**

## 3. Arquitectura observada

### Cliente
- Flutter/Dart, Material 3 y tema compartido.
- Riverpod para estado y carga asíncrona.
- go_router para navegación.
- Dio para llamadas HTTP al backend propio.
- fl_chart para gráficos e histórico.
- Integración de Firebase presente parcialmente; el funcionamiento debe comprobarse en cada entorno.
- Navegación adaptable: barra inferior en pantallas estrechas y NavigationRail en pantallas anchas.

El diseño de referencia indica que Flutter no debe llamar directamente a AEMET, RIA/IFAPA, SIGPAC o MAPA; debe hacerlo a través de la API propia.

### Backend
- FastAPI como API HTTP.
- Pydantic para esquemas.
- SQLite en los módulos trabajados.
- Motor de reglas en `backend/app/domain/disease_rules.py`.
- Esquemas en `backend/app/schemas.py`.
- API SIGPAC en `backend/app/api/sigpac.py` y su cliente asociado.
- Pruebas en `backend/tests/test_api.py`.

La arquitectura de referencia contempla también ingesta horaria, trabajos programados, caché offline avanzada, calibración y otras integraciones. No se consideran completas sin código, configuración y pruebas verificables.

## 4. Trabajo desarrollado

### 4.1 SIGPAC
- Se documentó el uso de SIGPAC HubCloud mediante OGC API – Features, colección predeterminada `recintos`.
- Hay endpoints internos para comprobar la integración, consultar recintos por extensión geográfica e importar recintos seleccionados.
- Se contempla guardar geometría GeoJSON y atributos en SQLite, con deduplicación.
- La interfaz permite delimitar una extensión y seleccionar identificadores de recintos.
- El mapa representa anillos exteriores de geometrías Polygon y MultiPolygon.

**Pendiente/limitaciones:** no se ha acreditado aquí conectividad en vivo en todos los entornos; no asumir paginación exhaustiva, tratamiento de huecos interiores o autoencuadre completo; la importación no implica necesariamente crear y vincular una parcela de negocio; tampoco está garantizado el acceso a campañas históricas.

Referencia: [docs/SIGPAC.md](SIGPAC.md), [PR #14](https://github.com/diezparaiso/agroalerta/pull/14).

### 4.2 Interfaz y navegación
- Ajustes al tema compartido Material 3 y estilos de componentes.
- Correcciones de textos, acentos y detalles en pantallas de acceso, parcelas, dispositivos e informes.
- Navegación adaptable por anchura de pantalla.
- Revisión de algunos textos del inicio para evitar presentar cifras de demostración como si fueran datos operativos.

**Pendiente:** comprobar móvil, tableta y escritorio; accesibilidad; rutas; estados de carga, error y vacío; consistencia visual. La navegación principal no representa necesariamente todas las pantallas previstas en la arquitectura.

### 4.3 Motor inicial de riesgo
Archivo principal: `backend/app/domain/disease_rules.py`.

La lógica actual:
- Relaciona repilo con olivar y mildiu con viñedo.
- Devuelve datos insuficientes cuando falta telemetría utilizable, la lectura tiene más de 24 horas, está fechada en el futuro o no corresponde al cultivo.
- Marca como `preliminar` los cálculos basados en telemetría reciente.
- Para repilo, usa como señal preliminar temperatura entre 15 y 20 °C y mojado foliar reportado de al menos 24 horas.
- Para mildiu, usa como señal provisional temperatura entre 10 y 25 °C, humedad relativa de al menos 85 % y mojado reportado de al menos 6 horas.
- Devuelve puntuación, nivel, confianza estimada, variables usadas, fecha de cálculo, caducidad y estado de los datos.
- Explica que el resultado no es una predicción validada y que no se debe tratar el cultivo basándose únicamente en el indicador.

**Precaución agronómica:** los umbrales de mildiu son provisionales. Una lectura aislada no demuestra mojado foliar continuo ni periodo de incubación. Se requiere serie temporal y validación con fuentes técnicas y especialistas; no usar el indicador por sí solo para decidir tratamientos.

### 4.4 Esquema de respuesta
En `backend/app/schemas.py`, `DiseaseRisk` incluye:
- `parcel_id`, `disease_code`
- `risk_score` de 0 a 1 y `risk_level` bajo/medio/alto
- `confidence_level` alta/estimada
- `recommendation_text`, `variables_used`
- `calculated_at`, `valid_until`
- `data_status`: `insuficiente` o `preliminar`

Se corrigió una duplicación de `data_status`; debe existir una sola definición y los clientes deben manejar ambos estados.

### 4.5 Lista de avisos
- La lista consume los registros del backend mediante ApiClient.
- Se eliminó el aviso ficticio de respaldo “Olivar de prueba” que aparecía si fallaba la API; ahora el error se propaga a la interfaz.
- Se muestra si el resultado es preliminar o si faltan datos.
- Se añadió un estado vacío explícito cuando la API devuelve cero avisos.

Esto diferencia una respuesta válida sin avisos de un fallo de red/API.

### 4.6 Detalle del aviso
Archivo: `lib/src/features/alerts/alert_detail_screen.dart`.

Se sustituyeron valores de demostración fijos —como lluvia 12,2 mm, temperatura 18,4 °C e índice 0,58— por la consulta de riesgo a la API. La pantalla:
- Filtra el resultado por código de enfermedad.
- Muestra nivel, puntuación, estado de datos, variables y explicación devueltos por el backend.
- Incluye estados de carga, error y ausencia de resultado.
- No presenta el gráfico de muestra como histórico real cuando no hay datos.
- Mantiene un aviso de que el indicador no es diagnóstico ni instrucción de tratamiento.

**Pendiente de comprobación importante:** la ruta debe pasar el ID de parcela del servidor, no su etiqueta visible. Hay que confirmar que los códigos de enfermedad de la ruta coinciden exactamente con `repilo` y `mildiu`, y que la API devuelve el cálculo esperado para esa parcela.

## 5. Registro de los cambios más recientes

| Commit | Cambio |
|---|---|
| `9991773` | Reemplaza datos ficticios del detalle por datos de la API. |
| `77d2ea5` | Ajusta el tipo numérico del indicador y el manejo de errores. |
| `4aa1025` | Añade estado vacío cuando no existen avisos. |

Estos commits se guardaron en `feature/sigpac-map-selection`. El mensaje de un commit acredita que se registró un cambio, no que haya superado las pruebas. El historial de la rama contiene además cambios previos en SIGPAC, presentación, esquema de riesgo, reglas preliminares y tratamiento de errores.

## 6. Pruebas y validación

**Presente en el repositorio:** pruebas en `backend/tests/test_api.py`, incluyendo flujo de parcela/riesgo, salud de API e integraciones. También se añadieron casos para datos insuficientes, telemetría antigua e indicador preliminar de mildiu.

**No confirmado en esta actualización:**
- No se ejecutó localmente la suite completa durante esta iteración.
- No se encontró una ejecución CI asociada al último commit consultado.
- No se puede afirmar que Flutter compile o que `flutter analyze` y `flutter test` pasen.
- No se puede afirmar que todos los tests backend pasen.
- No se ha acreditado una prueba end-to-end en dispositivos ni conectividad estable con fuentes externas en vivo.

**Validación necesaria:**
1. Ejecutar tests backend en el entorno del proyecto.
2. Ejecutar `flutter pub get`, `flutter analyze` y `flutter test`.
3. Probar el flujo lista → detalle con un ID real de parcela y ambos códigos de enfermedad.
4. Registrar enlaces/resultados CI y corregir fallos antes de declarar terminada la fase.

## 7. Deuda técnica y riesgos pendientes

1. Validar agronómicamente los umbrales por enfermedad, cultivo y zona.
2. Construir series temporales con fuente, marca temporal, calidad, estación y distancia a parcela.
3. Verificar contratos, disponibilidad y licencias de AEMET y RIA/IFAPA; no inventar endpoints.
4. Mostrar procedencia, hora de observación y antigüedad de datos.
5. Verificar que Flutter pasa el ID de parcela correcto, no el nombre.
6. Normalizar códigos de enfermedad entre interfaz y API.
7. Definir persistencia y semántica del histórico, y distinguir ausencia de datos de errores.
8. Completar paginación y geometrías complejas SIGPAC si lo exige el alcance, y vincular recinto importado con parcela.
9. Verificar autenticación y aislamiento de datos por propietario en cada entorno.
10. En productos MAPA, conservar fecha de consulta/versión de la fuente y no presentar dosis o plazos como actuales sin comprobar el registro.
11. Verificar de forma real el modo offline, caché, antigüedad y sincronización; que figure en la arquitectura no prueba que esté terminado.
12. Valorar separar la rama actual en PR temáticos: SIGPAC, UI y motor de riesgo, para facilitar revisión y reversión.

## 8. Plan de trabajo propuesto

### Prioridad 1 — Validación técnica
- Ejecutar tests backend, análisis Flutter y pruebas de interfaz.
- Corregir fallos y añadir tests para el detalle y los estados vacíos.
- Confirmar rutas, IDs de parcela y códigos de enfermedad.
- Obtener CI verificable.

### Prioridad 2 — Datos agroclimáticos
- Definir esquema de observaciones temporales con procedencia y calidad.
- Integrar fuentes documentadas y gestionar datos ausentes/obsoletos.
- Registrar distancia de estación y vigencia de cada observación.
- No inferir continuidad con una lectura aislada.

### Prioridad 3 — Motor de riesgo
- Validar umbrales con fuentes técnicas y especialistas.
- Probar con series históricas verificadas y casos negativos.
- Separar alerta heurística de modelo de incubación.
- Mantener recomendaciones no prescriptivas mientras no esté validado.

### Prioridad 4 — Integración del producto
- Vincular recintos SIGPAC con parcelas.
- Completar trazabilidad y estado de actualización en la UI.
- Verificar privacidad, permisos, notificaciones y despliegue.
- Registrar quién revisa y acepta cada entrega.

## 9. Criterios para considerar una funcionalidad terminada

Una funcionalidad solo se marcará como terminada cuando el código esté guardado, las pruebas pertinentes pasen con evidencia conservada, el flujo de interfaz se haya probado cuando corresponda, los estados de error/sin datos estén cubiertos, las limitaciones estén documentadas y una persona responsable revise y acepte el resultado.

## 10. Referencias
- [Repositorio](https://github.com/diezparaiso/agroalerta)
- [PR #14 — SIGPAC](https://github.com/diezparaiso/agroalerta/pull/14)
- [PR #15 — rama de trabajo](https://github.com/diezparaiso/agroalerta/pull/15)
- [Documentación SIGPAC](SIGPAC.md)
- Documento base: `AgroAlerta_Andalucia_Arquitectura_v2.docx`.
- Guía de desarrollo: `AgroAlerta_Andalucia_MasterPrompt_Desarrollo.docx`.

---

**Mantenimiento de esta memoria:** actualizarla en cada entrega con fecha, responsable, archivos afectados, hash de commit, pruebas ejecutadas, enlace CI, incidencias y decisión de aceptación. No registrar como verificado ningún resultado sin evidencia.


## 10. Actualización de verificación CI — 1 de octubre de 2026

Se ha comprobado en GitHub Actions la ejecución **#465** del flujo `AgroAlerta CI`, asociada al commit `0952e01333323c858dc1d5591ec6beead6696a46` de esta rama.

- Trabajo `flutter`: **success**. Los pasos `flutter pub get`, `flutter analyze` y `flutter test` finalizaron correctamente.
- Trabajo `backend`: **success**. La instalación de `backend/requirements.txt` y `PYTHONPATH=backend python -m pytest backend/tests -q` finalizaron correctamente.
- Ejecución: https://github.com/diezparaiso/agroalerta/actions/runs/36843152565

Esta evidencia confirma esos pasos para ese commit concreto. No equivale a validación agronómica, prueba con datos SIGPAC en vivo, auditoría de seguridad, ni garantía de funcionamiento en todos los dispositivos o entornos. Una modificación posterior requiere volver a comprobar su CI.


## 11. Revisión funcional y de aislamiento — 1 de octubre de 2026

**Responsable de la ejecución:** asistencia de desarrollo ChatGPT (OpenAI), a petición de la persona responsable del proyecto. No consta revisión humana independiente.

Cambios aplicados en la rama de trabajo:
- `b089a5a27e27f8b1200ed0555f62a6f78cf70a7a` — el detalle de parcela deja de aceptar `owner_id` como parámetro de consulta controlado por el cliente; ahora deriva el propietario de la identidad resuelta por la dependencia Bearer. La lectura de telemetría también comprueba el propietario y filtra por él.
- `61b5acb3691a7aa7987e7fbe73fef21b5a1858cd` — se elimina la lista de parcelas ficticias que aparecía cuando no había parcelas locales ni respuesta del backend. Un fallo de red ya no debe presentar parcelas de demostración como reales.
- `da741b864d984ff985c3f2443985b18efae7ed62` — se añaden pruebas para impedir que el parámetro `owner_id` permita consultar una parcela ajena y para comprobar el aislamiento de la lectura de telemetría.
- `f2c5b193083aa9c65bc97dda5eaa85023bc1e2df` — el formulario de parcelas usa el código de cultivo backend `vinedo` en vez de enviar el texto localizado `viñedo`.
- `3e629fe734b970a3e90a4c4e85bd1def32aef8bf` — la consulta SIGPAC ya no marca automáticamente el primer recinto como seleccionado; importar un recinto individual requiere selección explícita. Sin selección, el botón permite importar el área consultada.

**Verificación pendiente para esta revisión:** los cambios se han escrito en la rama y se han comprobado los SHA de los commits; en el momento de actualizar esta sección no hay un resultado CI asociado al último commit. Por tanto, las pruebas nuevas y el análisis Flutter de esta revisión están **pendientes de ejecución confirmada**.

**Límites de seguridad que siguen pendientes:** el modo sin Firebase configurado admite identidad basada en el token Bearer recibido, por lo que no debe considerarse autenticación de producción. Hay que decidir explícitamente el modo de desarrollo frente al de producción, exigir verificación criptográfica de identidad en producción y revisar todos los endpoints y tablas para asegurar aislamiento consistente. Esta revisión parcial no es una auditoría de seguridad completa.

**Datos todavía no operativos:** el endpoint meteorológico ya no devuelve las cifras de demostración como si fueran observaciones; responde `503` mientras no existan observaciones verificadas para esa parcela. El catálogo MAPA sigue siendo un marcador de integración pendiente, no un catálogo oficial sincronizado.


## 12. Autenticación en modo producción — 1 de octubre de 2026

Cambios adicionales en la rama:
- `ae9c09efd0d547216b3626f7674a294b99b0173a` — `optional_bearer_token` falla de forma cerrada si `ENVIRONMENT=production` y no hay credenciales de Firebase Admin; también exige cabecera Bearer en producción y verifica el token mediante Firebase cuando las credenciales están configuradas.
- `ce489f5552600b8cc4f9c1f76a35bd2f9546b5cd` — pruebas para el rechazo por configuración de autenticación ausente en producción y para exigir token.

**Estado de validación:** estas pruebas aún no se han ejecutado en una CI visible para los commits recientes. La prueba de autenticación configurada comprueba el rechazo por ausencia de token sin realizar una verificación real contra Firebase. La configuración de credenciales de producción, los permisos de los endpoints públicos y una auditoría integral siguen requiriendo revisión operativa.

## 13. Corrección de CI y selección SIGPAC — 1 de octubre de 2026

- `519e7016b40e514a9b0a798cdb29a84297dc64f4` — se elimina una variable local sin uso detectada por `flutter analyze` en `sigpac_map_screen.dart`.
- `82946da8f6ec2a4cf26ec936e929612dd8a3e8eb` — el backend reconoce también `properties.id` como identificador estable SIGPAC cuando el GeoJSON no contiene `feature.id`. Esto alinea la selección que envía Flutter con el filtrado de importación del backend.
- `ca90adb7f7d1f0d2716195b67949a5a07606f5d1` — prueba unitaria para la prioridad de identificadores GeoJSON y `properties.id`.
- `01bf1e65bb93283435f717d97a522d8ec47678a5` — una configuración Firebase Admin inválida devuelve un error controlado `503` en lugar de propagarse como error interno durante la inicialización.

**CI comprobado:** ejecución #474, https://github.com/diezparaiso/agroalerta/actions/runs/36847188541, finalizó con los trabajos `backend` y `flutter` en **success**. El análisis Flutter y los tests Flutter pasaron; también pasó `PYTHONPATH=backend python -m pytest backend/tests -q`. Esta ejecución se lanzó para el commit `519e7016...`; los commits posteriores de backend descritos arriba todavía necesitan una ejecución CI propia antes de considerarse verificados.

**Riesgos/pendientes detectados en revisión:** la ruta `/health/metrics` expone métricas de rutas sin autenticación y debe evaluarse según el despliegue; las rutas públicas de salud, catálogo y consulta SIGPAC deben documentarse como decisiones deliberadas. La autenticación de producción sólo protege rutas que declaran la dependencia, por lo que aún hace falta una auditoría completa del inventario de rutas y una prueba de integración con tokens Firebase reales. No se ha verificado en esta sesión la disponibilidad en vivo del proveedor SIGPAC.

## 14. Protección de métricas — 1 de octubre de 2026

- `1cd855ed89fb9abd04eda6ab6a2f825bc524c33e` — el endpoint `/health/metrics` usa la dependencia de autenticación compartida. En producción requiere token Bearer verificado por Firebase; en desarrollo mantiene el comportamiento previo.
- `593ba9a23e50b81b5883eb229a995ac9940b8300` — prueba de integración que confirma que una petición sin token a `/health/metrics` recibe HTTP 401 en modo producción cuando Firebase está configurado.

**Pendiente de verificación:** estos cambios se acaban de registrar y todavía no hay una ejecución CI confirmada para el último commit. Las rutas de salud e integraciones siguen siendo públicas deliberadamente para facilitar la comprobación de disponibilidad; antes de producción debe confirmarse que la información que exponen es apropiada para el despliegue.
