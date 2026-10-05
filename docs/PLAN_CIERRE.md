# Plan de cierre — AgroAlerta

> **MODIFICADO POR OPENCODE** — Documento creado en la Fase 0 (diagnóstico) el 2026-10-05 sobre la rama `feature/complete-agronomic-workflows`. Todo lo que sigue son resultados **ejecutados y observados** en esta máquina; nada está marcado como hecho sin haberse ejecutado.

---

## 1. Diagnóstico Fase 0a (resultados reales)

| Comando | Resultado observado | Notas |
|---|---|---|
| `flutter --version` | Flutter 3.47.1 stable, Dart 3.13.1, DevTools 2.60.0 | Canal stable |
| `flutter doctor -v` | 1 categoría con incidencias: Visual Studio sin componentes "Desktop development with C++" | Solo afecta a compilación de escritorio **Windows**, que no es objetivo. Android SDK 37, Chrome y licencias: OK |
| `flutter pub get` | `Got dependencies!` | 53 paquetes con versiones más nuevas **incompatibles con las restricciones**: NO se actualizan (regla 1). Se mantiene Riverpod 2.6.1, go_router 14.8.1, firebase_* 3.x/5.x |
| `flutter analyze --no-pub` | `No issues found! (ran in 64.1s)` | 0 incidencias |
| `flutter test` | `All tests passed!` | **1 test** (`test/widget_test.dart`) — cobertura muy baja |
| `python` del sistema | No existe en el PATH | El backend usa el venv de la máquina |
| venv `backend/.venv` | Python 3.13.15 (ya existente) | Coincide con DEVELOPMENT_NOTES |
| `pip install -r backend/requirements.txt` | Exit 0 | Instalación limpia |
| `PYTHONPATH=backend python -m pytest backend/tests -q` | **`33 passed, 1 warning in 4.02s`** | La única advertencia es un `DeprecationWarning` de starlette/anyio (compatibilidad futura, no bloquea) |
| `git status` | Árbol limpio | Rama `feature/complete-agronomic-workflows`, último commit `bff1099` |
| Espacio en disco `C:` | **3,9 GB libres** (confirmado por el usuario el 2026-10-05) | El build de APK se deja para el final de la Fase 4; antes de lanzarlo hay que volver a comprobar el espacio y **parar si hay menos de 3 GB** |

**Conclusiones del diagnóstico:**
- Todo lo que se puede ejecutar en local **está en verde hoy**: analyze 0, tests Flutter OK, 33 tests backend OK.
- **No existen las carpetas `web/` ni `ios/`** (solo `android/`): la app hoy no puede compilarse para Web ni iOS. Ese es el trabajo de la Fase 1.
- La suite Flutter tiene **un solo test**: ampliar cobertura es una tarea Alta del plan.
- El CI (`.github/workflows/ci.yml`) ejecuta `pytest`, `flutter pub get`, `flutter analyze`, `flutter test` — coincide con los comandos locales, pero **no ejecuta ningún build** (ni web ni APK).

---

## 2. Inventario de módulos Flutter (Fase 0b)

Leyenda de estado: **Funciona** = implementado y conectado a backend real · **Parcial** = funciona con limitaciones señaladas · **Bloqueado** = depende de credenciales/configuración externa.

| Módulo | Ruta | Estado | Fuente de datos | Observaciones verificadas |
|---|---|---|---|---|
| Arranque | `lib/main.dart` | Funciona | — | Arranque resiliente: Firebase, ads, notificaciones y cola offline envueltos en `try/catch`; `firebaseAvailableProvider` controla la UI |
| Navegación | `lib/src/app.dart` | Funciona | — | GoRouter con `ShellRoute`, 13 rutas, `NavigationBar` (<700 px) / `NavigationRail` (≥700 px, extendido ≥1100 px) |
| Resumen (home) | `features/home/` | Funciona | `weather`, `disease-risk`, `parcels`, `telemetry`, `farm/center` | 6 tarjetas; estados loading/error/vacío presentes. El error muestra texto ("Clima no disponible") **sin botón de reintento** |
| Parcelas | `features/parcels/` | Funciona | CRUD backend + `SharedPreferences` por `uid` | Coordenadas manuales o GPS (`geolocator`); fallback `offline-user` sin sesión |
| Avisos | `features/alerts/` | Funciona | `alerts`, `disease-risk`, `risk-history` | Detalle con variables, confianza, aviso legal y gráfica `fl_chart` de historial real |
| Productos | `features/products/` | Parcial | `GET /products` | Con catálogo vacío muestra *"Catálogo pendiente de sincronizar"* — **marcado explícitamente como pendiente, no como dato real** ✅ |
| Observaciones (reportes) | `features/reports/` | Parcial | `POST /field-reports` + cola offline (`connectivity_plus`) | ⚠️ Envía coordenadas **fijas 37.39/-5.99** en lugar de las de la parcela o GPS. Foto: `image_picker` (cámara) + subida a Firebase Storage solo en móvil |
| Sensores IoT | `features/devices/` | Funciona | `devices` | Alta y listado por parcela |
| Ajustes | `features/settings/` | Funciona | `health/integrations`, Auth | Privacidad (borrado local), consentimiento AdMob revocable, caché offline |
| Auth | `features/auth/` | Bloqueado | Firebase Auth (correo, Google, Apple) | Sin `google-services.json` / `firebase_options.dart` → `Firebase.initializeApp()` falla y la app entra en modo anónimo (`offline-user`). Login muestra "Configura Firebase para activar el acceso" |
| Explotación | `features/operation_center/` | Funciona | `GET /farm/center` | Estados loading/vacío OK |
| Campañas | `features/campaigns/` | Funciona | `parcels/{id}/campaigns`, `campaigns/{id}/status|summary|decisions` | Alta, cambio de estado, decisiones enlazadas |
| Resultados | `features/campaign_results/` | Funciona | `campaigns/{id}/results(/summary)` | Formulario de resultado y resumen de rendimiento |
| Línea temporal | `features/activity_timeline/` | Funciona | `parcels/{id}/activities`, `activity-timeline` | Estados loading/vacío OK |
| Decisión agronómica | `features/agronomic_decision/` | Funciona | `GET /agronomic-decision/{parcel}/{disease}` | Evidencia + próximos pasos |
| Riego | `features/irrigation/` | Parcial | `GET .../irrigation/intelligence` | ⚠️ El backend expone también `POST/GET .../irrigation/events`, que **Flutter no consume** |
| Anuncios (core/ads) | `core/ads/` | Funciona | AdMob (IDs de prueba) | Importación condicional con stub: **Web no muestra anuncios** ✅ |
| Notificaciones (core) | `core/notifications/` | Funciona | Locales + FCM | Locales con importación condicional (stub en Web) ✅; token FCM registrado solo si Firebase está disponible |
| Subida de fotos (core) | `core/storage/` | Funciona | Firebase Storage | Importación condicional con stub: Web no sube ✅ |
| Red/caché (core) | `core/network/` | Funciona | Dio + `SharedPreferences` | `ApiClient` con token Bearer si hay sesión |
| Ubicación (core) | `core/location/` | Parcial | `geolocator` | Importación directa: funciona en Web con permiso del navegador; en iOS requiere claves de `Info.plist` (Fase 1) |

**Datos ficticios:** la búsqueda en `lib/` de `mock|demo|fictic|dummy|sample` **no devuelve resultados**. La retirada de datos inventados del 2026-09-30 se mantiene. Únicos puntos a vigilar: el placeholder explícito de productos (correcto) y las coordenadas fijas del formulario de observación (a corregir).

---

## 3. Inventario de backend (Fase 0b)

### Endpoints (35 registrados en `backend/app/main.py`)

| Grupo | Endpoints | Estado |
|---|---|---|
| Salud | `GET /health`, `/health/integrations`, `/health/metrics` | Documentados y probados (33 tests) |
| Parcelas | `GET/POST /parcels`, `GET/PUT/DELETE /parcels/{id}` | Documentados |
| Clima y riesgo | `GET /weather/{id}`, `/disease-risk/{id}`, `/alerts`, `/risk-history/{id}` | Documentados; datos reales con 503 explícito (ADR-007) |
| Productos/reportes | `GET /products`, `POST /field-reports` | Documentados |
| IoT | `POST/GET /devices`, `POST/GET /telemetry` | Documentados |
| Notificaciones | `POST /push-tokens`, `DELETE /push-tokens/{token}` | Documentados |
| Explotación | `GET /farm/center` | Documentado |
| Campañas/resultados | 9 endpoints de campaigns/decisions/results | Documentados |
| **Operación agronómica** | `POST/GET /parcels/{id}/activities`, `GET /parcels/{id}/activity-timeline`, `POST/GET /parcels/{id}/irrigation/events`, `GET /parcels/{id}/irrigation/intelligence`, `GET /agronomic-decision/{id}/{disease}` | ⚠️ **NO documentados en `API_CONTRACTS.md`** → tarea de documentación (Alto) |

### Conectores y servicios

| Componente | Estado verificado | Limitaciones detectadas en código |
|---|---|---|
| `aemet_client.py` | OK en vivo 2026-10-01 (docs) — requiere `AEMET_API_KEY` de `.env`, nunca se imprime | `timeout=15`, `raise_for_status()`; **sin reintentos ni control de cuota explícito** |
| `ria_ifapa_client.py` | OK en vivo 2026-09-29 (docs, sin credenciales) | `timeout=15`, `raise_for_status()`; **sin reintentos** |
| `weather_service.py` | Orquestador RIA → AEMET → 503 con motivo real | Cumple "nunca inventar datos" (ADR-007) |
| `mapa_catalog.py` | Importador CSV versionado | Contrato público **sin verificar** + pendiente legal de exportación/indexación |
| `fcm_dispatcher.py` | Reintentos (3, backoff exponencial), limpieza de tokens inválidos, circuit breaker 60 s | Solo con `FIREBASE_SERVICE_ACCOUNT_JSON` |
| Jobs (`weather_ingestion`, `risk_recalculation`) | Preparados para cron/Celery/Cloud Run | Ejecución programada externa pendiente |

### Tests backend
`33 passed` — 11 ficheros: `test_api`, `test_weather_service`, `test_aemet_client`, `test_disease_rules`, `test_agronomic_decision`, `test_campaign_*` (3), `test_activity_timeline`, `test_farm_operation_center`, `test_irrigation_intelligence`.

---

## 4. Dependencias con soporte limitado por plataforma (Fase 0c)

| Paquete | Web | iOS | Protección actual | Acción necesaria |
|---|---|---|---|---|
| `flutter_local_notifications` 18.0.1 | ❌ no soportado | ✅ | ✅ Importación condicional con stub (`notification_service.dart`) | Claves de permiso en `Info.plist` (Fase 1) |
| `google_mobile_ads` 9.1.0 | ❌ no soportado | ✅ | ✅ Importación condicional con stub (`ads_service.dart`, `ad_banner.dart`) | `GADApplicationIdentifier` en `Info.plist` **solo con ID real** (pendiente tuyo) |
| `firebase_storage` 12.x | ⚠️ requiere config Firebase | ✅ | ✅ Importación condicional con stub (`photo_upload.dart`) | — |
| `firebase_messaging` 15.x | ⚠️ requiere config Firebase | ✅ ⚠️ necesita APNs | ⚠️ Importación **directa** en `main.dart` dentro de `try/catch` | Verificar en Fase 1 que en Web no lanza fuera del `catch`; APNs solo con certificados |
| `firebase_core` / `firebase_auth` | ⚠️ **sin `firebase_options.dart`**: `Firebase.initializeApp()` sin opciones falla siempre en Web | ⚠️ requiere `GoogleService-Info.plist` | ✅ Degradado controlado (`firebaseAvailable=false`) | Configuración Firebase real (pendiente tuya); NO se simula |
| `google_sign_in` 6.2.2 | ⚠️ necesita OAuth Client ID web | ⚠️ necesita URL scheme | Importación directa en `auth_service.dart` (no rompe compilación) | Credenciales (pendiente tuyo) |
| `sign_in_with_apple` 6.1.4 | ✅ impl. web | ⚠️ requiere capability + certificado Apple | Importación directa | **NO añadir capability sin certificados**; guía en `docs/IOS_BUILD.md` |
| `geolocator` 13.x | ⚠️ permiso de navegador + HTTPS | ⚠️ requiere `NSLocation*UsageDescription` | Importación directa en `location_service.dart` | Claves de `Info.plist` (Fase 1); fallback si el permiso se deniega (Fase 3) |
| `image_picker` 1.1.2 | ✅ (input de archivo) | ⚠️ requiere `NSCameraUsageDescription` / `NSPhotoLibraryUsageDescription` | Importación directa | Claves de `Info.plist` (Fase 1) |
| `connectivity_plus` 6.x | ✅ | ✅ | — | — |
| `flutter_map` 7 / `fl_chart` 0.69 / `latlong2` | ✅ | ✅ | — | Verificar render en Web (Fase 3) |
| `dio`, `flutter_riverpod` 2.x, `go_router` 14.x, `shared_preferences` | ✅ | ✅ | — | Mantener versiones (regla 1) |

**Resumen de protección Web:** los cuatro puntos móviles críticos (notificaciones locales, AdMob, subida de fotos, FCM) ya están tras importaciones condicionales **o** dentro de `try/catch`; los restantes (`geolocator`, `image_picker`, `google_sign_in`, `flutter_map`) compilan en Web pero requieren permisos/configuración de navegador. Falta **demostrarlo ejecutando** `flutter build web` (Fase 1).

---

## 5. Riesgos

| # | Riesgo | Impacto | Mitigación en el plan |
|---|---|---|---|
| R1 | Sin carpetas `web/` ni `ios/` no hay build multiplataforma | Crítico | Fase 1 |
| R2 | Firebase sin configurar: auth anónima (`offline-user`) en todas las plataformas | Alto | Se documenta; NO se inventa configuración. Pendiente del usuario |
| R3 | Solo 1 test Flutter (sin tests responsive ni de modelos) | Alto | Fase 3 |
| R4 | `API_CONTRACTS.md` incompleto (5 grupos de endpoints sin documentar) | Alto | Fase 2 |
| R5 | Conectores sin reintentos ni manejo de cuota AEMET | Medio | Fase 2 (medir y documentar; reintento solo si se justifica) |
| R6 | `report_screen.dart` envía coordenadas fijas 37.39/-5.99 | Medio | Fase 3 (usar parcela o GPS) |
| R7 | Espacio de disco limitado: el build Android ya falló por disco lleno el 2026-10-01 | Medio | Fase 4: comprobar espacio antes de compilar el APK; si hay menos de 3 GB, parar y avisar (margen acordado: 3,9 GB libres hoy) |
| R8 | iOS **no compilable desde Windows** (sin Xcode) | Aceptado | `docs/IOS_BUILD.md` + guía para Mac (Fase 1) |
| R9 | CI no ejecuta builds (solo analyze/test) | Bajo | Fase 4: alinear CI con la secuencia de cierre |
| R10 | `applicationId` `com.example.agroalerta_andalucia` no publicable | Bloqueante al publicar | Anotado; decisión del usuario. NO se cambia sin preguntar |
| R11 | Eventos de riego del backend sin consumir en Flutter | Medio | Fase 3: conectar o documentar fuera de alcance (preguntar) |
| R12 | Umbrales de error sin "reintento" en varias pantallas (solo texto) | Medio | Fase 3 |

---

## 6. Tareas priorizadas y orden propuesto

### Crítico
1. **F1.1** Generar plataformas `web/` e `ios/` (`flutter create --platforms=web,ios`) sin tocar `lib/`, `android/` ni `pubspec.yaml`; verificar con `git status`.
2. **F1.2** Configurar `web/index.html` y `web/manifest.json` (español, lang `es`) y proteger la app en Web para que arranque sin excepciones.
3. **F1.3** `flutter build web --release` en verde.
4. **F2.1** Arrancar uvicorn y verificar los 35 endpoints reales contra `API_CONTRACTS.md` (códigos, forma, errores sin trazas/secretos, CORS).
5. **F2.2** Verificar AEMET y RIA/IFAPA en vivo con llamadas mínimas (sin exponer la clave) y su comportamiento con la API caída.

### Alto
6. **F1.4** `Info.plist` de iOS con textos de permisos en español + `docs/IOS_BUILD.md` (declarando que iOS no se compila en Windows).
7. **F2.3** Completar `API_CONTRACTS.md` con actividades, riego (incluidos `POST/GET .../irrigation/events`) y decisión agronómica.
8. **F2.4** Tests de conectores con respuestas de ejemplo guardadas; pytest en verde.
9. **F2.5** **Verificación de autenticación/autorización** (decisión del usuario 2026-10-05): para cada endpoint probar sin token, con token inválido y con token de otro usuario; comprobar si un usuario puede leer/modificar parcelas de otro. Documentar resultado y riesgos en la documentación; **no cambiar el modelo de auth sin preguntar**.
10. **F2.6** **Reintentos y caché en conectores** (decisión del usuario 2026-10-05): 2-3 reintentos con espera creciente **solo** ante timeout/5xx/429, más caché razonable para respetar la cuota de AEMET.
11. **F2.7** Comprobar si la interfaz cita AEMET/RIA como fuente; si el nivel de detalle no basta, anotarlo y preguntar al usuario.
12. **F3.1** `flutter analyze --no-pub` sin incidencias durante toda la fase.
13. **F3.2** Widget tests responsive (360×640, 768×1024, 1280×800) que detecten desbordamientos.
14. **F3.3** Ampliar tests Flutter: modelos/serialización, providers con repositorios simulados, reglas de riesgo (sin red real).
15. **F3.4** Revisar estados de error con reintento, validación de formularios, textos en español y accesibilidad en todas las pantallas.

### Medio
16. **F3.5** Coordenadas del formulario de observación (decisión del usuario 2026-10-05): **ubicación del dispositivo con permiso → si se niega, centro de la parcela → si no hay parcela, aviso en pantalla**. Nunca coordenadas inventadas.
17. **F3.6** Caché razonable del clima y respeto de límites de API.
18. **F3.7** Verificar `flutter_map`, `fl_chart` y geolocalización en Web (permisos y fallback).
19. **F3.8** Eventos de riego (decisión del usuario 2026-10-05): documentar los endpoints en Fase 2 y **conectarlos en Fase 3 solo si `irrigation_screen.dart` ya existe y el contrato es simple**; si requiere pantallas nuevas, dejarlo como pendiente.
20. **F3.9** Revisar auth (flujo, errores y configuración por plataforma) sin simular credenciales.
21. **F3.10** Atribución de fuente en la interfaz: hoy se muestra `Fuente: ria-ifapa|aemet` en la tarjeta de clima. Pendiente de decisión del usuario si se amplía a nombre institucional (p. ej. "AEMET — Agencia Estatal de Meteorología") y/o en el detalle de avisos.

### Bajo (no bloquean el cierre técnico)
22. **F4.1** CI: añadir el paso de build **igualando los comandos realmente ejecutados** en la Fase 4 (build web y, si procede, APK).
23. **F4.2** Actualizar `PROJECT_LEDGER.md`/`DEVELOPMENT_NOTES.md` con marcadores "MODIFICADO POR OPENCODE".

### Pendientes que dependen del usuario (no se tocan)
- Firebase: `flutterfire configure` → `google-services.json`, `GoogleService-Info.plist`, `firebase_options.dart`.
- IDs reales de AdMob y consentimiento en tiendas.
- OAuth Client ID de Google (web/Android/iOS) y capability/certificado de Apple Sign In (Apple Developer).
- Cambio de `applicationId`/firma antes de publicar (Android `com.example.agroalerta_andalucia` e iOS `com.example.agroalertaAndalucia`).
- Pruebas en dispositivo real Android e iPhone.
- **Despliegue del backend** (decisión del usuario 2026-10-05): hosting, base de datos de producción (sustituto de SQLite) y cron/planificación de los jobs de ingesta y recálculo.

### Orden de ejecución propuesto
`Fase 0 (completada)` → **Fase 1 (plataformas)** → **Fase 2 (backend/APIs)** → **Fase 3 (calidad Flutter/UI)** → **Fase 4 (cierre y construcción)**. Cada fase termina con resumen y commits convencionales.

---

## 7. Criterios de verificación mínimos por fase

- **Fase 1:** `git status` sin cambios inesperados en `lib/`, `android/` o `pubspec.yaml` · app arranca en Chrome sin excepciones · `flutter build web --release` OK · `docs/IOS_BUILD.md` creado.
- **Fase 2:** tabla endpoint-a-endpoint con código HTTP real · verificación en vivo de AEMET/RIA sin volcar la clave · pytest en verde.
- **Fase 3:** `flutter analyze --no-pub` a 0 · tests responsive en verde · tests de modelos/providers añadidos.
- **Fase 4:** `flutter analyze --no-pub` + `flutter test` + `flutter build web --release` + `flutter build apk --debug` + `pytest` — todos anotados con su resultado real.
