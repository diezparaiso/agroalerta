# Notas de desarrollo

## Estado

AgroAlerta Andalucia es una aplicación Flutter responsive con backend FastAPI para avisos fitosanitarios en olivar y vinedo. El cliente está preparado para Android, iOS y Web; el backend concentra las fuentes externas y el cálculo de riesgo. La meteorología se sirve desde fuentes reales (RIA/IFAPA primero y AEMET como respaldo) y, cuando no hay evidencia, se expresa ausencia explícita en lugar de datos de demostración.

## Implementado

### Cliente Flutter

- Navegación responsive con `NavigationBar` en móvil y `NavigationRail` en tablet/escritorio.
- Tema Material 3 claro/oscuro.
- Dashboard con clima, telemetría, mapa y resumen de riesgo.
- Gestión de parcelas con coordenadas manuales o GPS.
- Persistencia local de parcelas por usuario mediante `SharedPreferences`.
- Modo offline y cola de reportes pendientes.
- Reportes de campo de síntomas o trampas.
- Captura de fotografías y subida preparada a Firebase Storage.
- Alertas con detalle, variables usadas, confianza y aviso legal.
- Notificaciones locales para riesgos medios y altos.
- Registro FCM del dispositivo para notificaciones remotas.
- Registro y consulta de sensores IoT por parcela.
- Lectura de telemetría: temperatura, humedad, mojado foliar, suelo y batería.
- Autenticación Firebase: Google, Apple, correo, registro y recuperación de contraseña.
- Onboarding por usuario con comarca y cultivos de interés.
- Consentimiento y revocación de publicidad AdMob.
- Gestión de privacidad: borrado de datos locales.
- Arranque resiliente: servicios opcionales no bloquean la apertura de la app.

### Backend FastAPI

- API versionada bajo `/api/v1`.
- Persistencia SQLite local para desarrollo.
- CRUD de parcelas.
- Endpoints de clima, riesgo, alertas, productos y reportes.
- Motor inicial de riesgo para repilo y mildiu.
- Uso prioritario de telemetría IoT cuando existe.
- Registro de sensores y dispositivos por parcela.
- Ingesta y consulta de telemetría.
- Registro de tokens FCM.
- Tokens FCM persistidos en SQLite por propietario y plataforma.
- Verificación Firebase Admin preparada para tokens Bearer cuando existe `FIREBASE_SERVICE_ACCOUNT_JSON`.
- Parcelas con `owner_id` y filtrado por propietario en listado, actualización y borrado.
- Reportes, telemetría, dispositivos y tokens FCM reciben el `owner_id` verificado.
- SQLite migra tablas IoT antiguas y filtra telemetría, dispositivos y alertas por propietario.
- Historial de snapshots de riesgo por parcela y enfermedad, filtrado por propietario.
- Dispatcher preparado para Firebase Admin.
- Job de recálculo conectado a tokens FCM persistidos para riesgos medios y altos.
- Job FCM compara el nivel anterior y notifica solo cuando el riesgo aumenta.
- Tokens FCM que fallan se eliminan automáticamente tras un envío fallido.
- FCM reintenta tres veces con backoff exponencial antes de eliminar un token.
- Circuit breaker FCM pausa 60 segundos tras una caída prolongada.
- Endpoint `/health/integrations` para diagnosticar servicios configurados sin exponer secretos.
- `/health` comprueba SQLite y devuelve versión del servicio.
- Middleware registra método, ruta, estado y duración sin incluir secretos.
- Contratos HTTP documentados en `API_CONTRACTS.md`.
- Endpoint `/health/metrics` expone contador y latencia media por ruta.
- Conectores aislados para AEMET y RIA/IFAPA.
- Importador CSV para catálogo MAPA.
- Jobs de ingesta y recálculo de riesgos.
- Docker y configuración por entorno.
- Docker Compose incluye reinicio automático y healthcheck de la API.
- Prueba de regresión de aislamiento de parcelas entre usuarios.
- Historial persistente de snapshots de riesgo por parcela y enfermedad.
- Deduplicación temporal de snapshots idénticos para evitar crecimiento innecesario.
- Historial paginado con `limit` y `offset` para consultas grandes.
- Retención de snapshots configurable mediante `RISK_SNAPSHOT_RETENTION_DAYS`.
- Gráfica Flutter de evolución del riesgo en el detalle de alerta, conectada a snapshots reales sin datos de demostración.
- Fixture de pruebas que limpia SQLite entre casos para evitar contaminación de datos.
- Prueba de regresión que garantiza deduplicación de snapshots repetidos.
- Prueba de salud que confirma que no se exponen credenciales de integraciones.
- Prueba de contrato para paginación de historial.
- Orquestador `app/core/weather_service.py` y endpoint `GET /api/v1/weather/{parcel_id}`: RIA/IFAPA primero, AEMET con `AEMET_API_KEY` y error 503 explícito cuando no hay fuente disponible.
- Cliente RIA/IFAPA reescrito sobre los endpoints oficiales verificados en vivo (`/estaciones` y `/datosdiarios/forceEt0/{provincia}/{estacion}/{desde}/{hasta}`).
- Nuevos campos de respuesta `station_name` y `source` (`ria-ifapa` o `aemet`) junto a `temperature_c`, `relative_humidity`, `rainfall_mm_24h`, `station_distance_km` y `observed_at`.
- 9 pruebas nuevas del servicio meteorológico en `backend/tests/test_weather_service.py` (31 tests en total entonces; 33 desde el 2026-10-01).

## Decisiones técnicas

- `SharedPreferences` funciona como caché inicial multiplataforma para no bloquear Web. Puede sustituirse por Isar cuando se cierre la estrategia Web.
- Los datos meteorológicos son reales: RIA/IFAPA primero (sin credenciales) y AEMET solo si existe `AEMET_API_KEY`; sin fuente disponible se devuelve ausencia explícita (HTTP 503), nunca valores inventados (ADR-007). El catálogo MAPA sigue pendiente de validar su contrato público.
- AdMob se muestra solo en pantallas generales; nunca en alertas o recomendaciones fitosanitarias.
- La publicidad requiere consentimiento persistente y revocable.
- Las fotografías deben pasar por Firebase Storage; no se deben enviar rutas locales al backend en producción.
- Las recomendaciones son orientativas y deben conservar trazabilidad de fuente MAPA.
- Los tokens de usuario deben verificarse en backend antes de producción y cada parcela debe filtrarse por propietario.

## Estado de la integración meteorológica (verificación 2026-09-30)

### Qué se hizo

- Backend: nuevo orquestador `app/core/weather_service.py` que alimenta `GET /api/v1/weather/{parcel_id}`. Orden de fuentes: RIA/IFAPA → AEMET (solo si existe `AEMET_API_KEY`) → error HTTP 503 con el motivo real. En ningún caso se inventan valores (ADR-002 y ADR-007).
- `ria_ifapa_client.py` reescrito con los endpoints oficiales verificados en vivo: `GET {ria_base_url}/estaciones` y `GET {ria_base_url}/datosdiarios/forceEt0/{provincia}/{estacion}/{desde}/{hasta}` (el formato anterior de URL estaba roto).
- Selección de estación: la estación activa no plástica más próxima a la parcela por distancia haversine sobre el catálogo en vivo; para AEMET, la capital andaluza del INE más próxima (aproximación documentada en ADR-007).
- Flutter: eliminados todos los datos ficticios de `weather_provider.dart`, `alerts_provider.dart`, `parcel_provider.dart` (getter demo), `alert_detail_screen.dart` (puntuación, métricas, nombre de parcela y gráfica inventados) y `risk_history_chart.dart` (serie por defecto). Se conservan la caché offline local de parcelas y las notificaciones locales best-effort, que no son datos inventados.
- Correcciones incluidas: bug real de desempaquetado de tupla en la selección de estación (detectado por las nuevas pruebas), desbordamiento de 196 px en `login_screen.dart` (envuelto en `SingleChildScrollView`) y `test/widget_test.dart` roto (envuelto en `ProviderScope`).
- Desbloqueo 2026-10-01 (`AEMET_API_KEY`): `config.py` migrado a `pydantic-settings` con `env_file` apuntando a la raíz del proyecto (el `.env.example` existía pero nada cargaba el `.env`); la clave real vive en `.env` (gitignored). El conector AEMET decodifica ahora el charset declarado por la API (`ISO-8859-15`, no UTF-8) y el parser acepta la estructura real del diario (`prediccion.dia` con `{'maxima', 'minima', 'dato'}`).

### Validación ejecutada

- Backend: `31 passed` con `PYTHONPATH=backend python -m pytest backend/tests -q` el 2026-09-30 (9 pruebas nuevas del servicio meteorológico) y `33 passed` desde el 2026-10-01 con las 2 pruebas nuevas de AEMET.
- Flutter: `flutter test` en verde; `flutter analyze` sin incidencias en los archivos tocados por este cambio y en todo el proyecto tras corregir las 24 incidencias preexistentes el mismo día.
- Prueba en vivo contra RIA/IFAPA con una parcela temporal (creada y borrada después): 24,3 °C, humedad 65,1 %, estación "La Rinconada" a 9,4 km, observado el 2026-09-29, `source: ria-ifapa`.
- Prueba en vivo de AEMET el 2026-10-01 con la clave real: predicción diaria de Sevilla (INE 41091) con 26,0 °C, humedad 65,0 %, `rainfall_mm_24h: null` y `observed_at: 2026-09-30`; el fallback completo con RIA caída devuelve `source: aemet`; `GET /health/integrations` responde `ria_ifapa: live` y `aemet: live`.

### Incidencias y limitaciones conocidas

- Las 24 incidencias preexistentes de `flutter analyze` (imports sin usar, `value` deprecated en `DropdownButtonFormField` y concatenaciones con `+`) se corrigieron el 2026-09-30; `flutter analyze` queda en 0 incidencias y el paso de análisis de CI pasa.
- AEMET quedó verificado en vivo el 2026-10-01 con `AEMET_API_KEY` real guardada en `.env` (caduca el 2027-01-09). La API declara `charset=ISO-8859-15` (no UTF-8) y su diario devuelve `prediccion.dia` con `{'maxima', 'minima', 'dato'}`; conector y parser ya cubren esos formatos. En fuente AEMET, `rainfall_mm_24h`, `station_name` y `station_distance_km` quedan `null` por ser predicción municipal sin milímetros publicados: ausencia explícita, no valores inventados.
- La combinación ponderada de hasta tres estaciones y el límite de 80 km descritos en el ADR-003 quedan diferidos; el alcance real está registrado en el ADR-007.
- Entorno de la máquina de desarrollo: Python 3.13.15 con virtualenv en `backend/.venv` (gitignored) y ~8 GB de RAM. La compilación nativa Android se intentó el 2026-10-01: el daemon JVM de Gradle crasheaba por memoria con los valores por defecto de la plantilla (`-Xmx8G`), ya corregidos en `android/gradle.properties`, y el proceso quedó después bloqueado por disco lleno (quedaban ~733 MB). Falta reanudar `flutter build apk --debug` cuando haya espacio.

## Pendientes de producción

1. Ejecutar `flutterfire configure` y añadir configuración Firebase para Android, iOS y Web.
2. Crear los proyectos y credenciales reales de AdMob.
3. Verificar Firebase Storage Rules y Firebase Auth providers.
4. Sustituir SQLite por PostgreSQL/PostGIS en despliegue.
5. Conectar métricas a almacenamiento o Prometheus y panel Flutter de salud.
6. Conectar los datos horarios de RIA/IFAPA (los datos diarios ya están conectados mediante `/datosdiarios/forceEt0`).
7. Verificar mecanismo de exportación o indexación legal del registro MAPA.
8. Añadir métricas de retención y carga incremental en la gráfica Flutter.
9. Configurar permisos nativos de cámara, ubicación, notificaciones y AdMob.
10. Pruebas en local completadas: backend 33/33 (2026-10-01), `flutter test` en verde y `flutter analyze` sin incidencias. Queda ejecutar las pruebas en Android, iOS y Web.
11. Reanudar la compilación Android (`flutter build apk --debug`) cuando haya disco libre y completar el manifest de release: permisos `INTERNET`, ubicación y notificaciones, más el meta-data `APPLICATION_ID` de AdMob.

## Última validación

- Estado global a 2026-10-01: suite backend completa en verde con 33 tests (31 el 2026-09-30 y 2 de AEMET añadidas el 2026-10-01), `flutter test` en verde y `flutter analyze` sin incidencias (las 24 preexistentes se corrigieron el 2026-09-30). La serie siguiente registra la evolución histórica de los 6 tests originales de `test_api.py`.
- Backend: `6 tests passed` en `backend/tests/test_api.py` tras añadir historial y aislamiento.
- El endpoint de clima quedó protegido por propietario; la suite mantiene `6 tests passed`.
- Tokens FCM persistidos; la suite mantiene `6 tests passed`.
- Dispatcher FCM y job de riesgo conectados; la suite mantiene `6 tests passed`.
- Notificaciones deduplicadas por subida de nivel; la suite mantiene `6 tests passed`.
- Limpieza automática de tokens inválidos; la suite mantiene `6 tests passed`.
- Salud de integraciones añadida; la suite mantiene `6 tests passed`.
- Health check con SQLite y versión; la suite mantiene `6 tests passed`.
- Métricas de petición añadidas; la suite mantiene `6 tests passed`.
- Retención configurable de snapshots; la suite mantiene `6 tests passed`.
- Historial paginado en backend y cliente; la suite mantiene `6 tests passed`.
- Métricas de contador y latencia media por ruta; la suite mantiene `6 tests passed`.
- Las advertencias restantes proceden de compatibilidad futura entre Starlette/anyio y Python; la validación de 2026-09-30 se ejecutó con Python 3.13.15.

## Comandos previstos

```bash
python -m pip install -r backend/requirements.txt
PYTHONPATH=backend python -m pytest backend/tests -q
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

En la máquina de desarrollo (2026-09-30) el backend se ejecuta con el entorno virtual `backend/.venv` (Python 3.13.15). En PowerShell:

```powershell
$env:PYTHONPATH='backend'; & "backend\.venv\Scripts\python.exe" -m pytest backend/tests -q
```

## MODIFICADO POR OPENCODE — 2026-10-05/06 (plan de cierre)

- **Fase 1:** plataformas `web/` e `ios/` añadidas sin tocar `lib/`, `android/` ni `pubspec.yaml`; `flutter build web --release` OK y 13 rutas verificadas en Chrome (commit `12fbc25`).
- **Fase 2:** corregidos `irrigation_events` (tabla inexistente → `500`), persistencia de columnas de `campaign_results` (`yield_kg_ha`, `target_yield_kg_ha`, `target_deviation_pct`) y tolerancia a `null` en `agronomic_decision`.
- Reintentos de conectores en `app/connectors/http_retry.py` (timeout/5xx/429, espera creciente, 3 intentos máx.) y caché AEMET de 6 h por municipio en `weather_service.py`.
- `ApiClient` envía peticiones aunque no haya Firebase (interceptor con `try/catch`), cubierto por `test/api_client_test.dart`.
- Estado verificado 2026-10-06: `pytest` **50 passed**, `flutter analyze --no-pub` **0 issues**, `flutter test` **3 passed**, verificación en vivo **77 comprobaciones / 0 fallos**.
- Aviso de disco: `C:` llegó a 2,23 GB (un `flutter test` falló por espacio); tras limpiar cachés de Gradle quedan 3,52 GB. Umbral: no construir el APK con menos de 3 GB.
- **Fase 3 (2026-10-06, commits `4680623`, `88e1901`, `d6db6e3`):** coordenadas del formulario por GPS → centro de parcela → aviso (`ParcelSummary` sin coordenadas por defecto); widget `ErrorView` con «Reintentar» en 14 puntos; eventos de riego conectados en `irrigation_screen.dart`; caché de clima en `OfflineCache` marcada `cached: true`.
- **Tests:** `flutter test` pasó de 3 a **29** (responsive 5 pantallas × 3 tamaños con detección de desbordamientos, modelos, caché de clima, mapa con `flutter_map` y gráfico con `fl_chart`); `flutter analyze --no-pub` → 0 issues; `pytest` → 50 passed.
- **CORS de desarrollo (F3.7):** `backend/app/main.py` acepta `allow_origin_regex` `^http://localhost(:\d+)?$` cuando `ENVIRONMENT != production` (el servidor estático en 8080 y `flutter run -d chrome` usan puertos variables). Preflight verificado: 400 → 200 con `access-control-allow-origin`. En producción solo valen los orígenes de `CORS_ALLOWED_ORIGINS`.
- **Auth (F3.9):** sin cambios en el modelo; cancelar el acceso con Google ya no muestra error y el cierre de sesión avisa si falla. En Web la app sigue en la pantalla de login hasta ejecutar `flutterfire configure` (pendiente del usuario).
