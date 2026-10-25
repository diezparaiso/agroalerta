# AGENTS.md

## Comandos esenciales

### Backend (FastAPI + SQLite)

```bash
# Instalar dependencias
python -m pip install -r backend/requirements.txt

# Ejecutar tests (requiere PYTHONPATH=backend)
PYTHONPATH=backend python -m pytest backend/tests -q

# Ejecutar un solo test
PYTHONPATH=backend python -m pytest backend/tests/test_api.py::test_health -q

# Levantar servidor de desarrollo
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000

# Docker
docker compose up --build
```

### Cliente Flutter

```bash
flutter pub get
flutter analyze
flutter test

# Ejecutar en Chrome con backend local
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000

# Ejecutar en Android con AdMob
flutter run -d android --dart-define=API_BASE_URL=http://localhost:8000 --dart-define=ADMOB_BANNER_ID=ca-app-pub-xxxxxxxxxxxxxxxx/xxxxxxxxxx
```

## Arquitectura

- **Backend**: `backend/app/` — FastAPI con capas `core/` (storage, security, config), `domain/` (reglas de negocio puras), `connectors/` (AEMET, RIA/IFAPA, MAPA), `jobs/` (ingesta y recálculo), `notifications/` (FCM).
- **Cliente**: `lib/src/` — Riverpod + go_router. Núcleo en `core/` (ads, network, notifications, storage, theme, location, privacy). Features en `features/` (auth, parcels, alerts, campaigns, irrigation, etc.).
- **Persistencia dual**: SQLite en backend (`backend/agroalerta.db`, gitignored). `SharedPreferences` en Flutter como caché local por `uid`.
- **Plataforma condicional**: Ads, notificaciones y subida de fotos usan exports condicionales (`stub` para web, `mobile` para iOS/Android). No añadir imports directos de `dart:io` en código compartido.

## Convenciones importantes

- **Idioma**: Todo el código, comentarios y documentación en español de España.
- **PYTHONPATH**: Obligatorio prefijar `PYTHONPATH=backend` en todos los comandos de backend (pytest, uvicorn).
- **Firebase es opcional**: La app arranca sin Firebase (modo anonymous/local). En producción, `ENVIRONMENT=production` requiere `FIREBASE_SERVICE_ACCOUNT_JSON`.
- **Tests backend**: El fixture `clean_database` (autouse) limpia SQLite entre tests. No dependas de datos persistentes.
- **Esquemas Pydantic v2**: Los modelos en `schemas.py` y `schemas_push.py` definen los contratos HTTP. Validarlos antes de modificar endpoints.
- **Reglas de negocio en `domain/`**: Los módulos de dominio son funciones puras o casi puras. No añadir lógica de HTTP ni persistencia ahí.
- **Sin datos ficticios en producción**: Si una fuente real no está disponible, el sistema debe expresar ausencia o baja confianza, no inventar datos.

## CI

GitHub Actions (`.github/workflows/ci.yml`) ejecuta en cada push a `main` y en PRs:
1. Tests del backend (`PYTHONPATH=backend python -m pytest backend/tests -q`)
2. `flutter pub get` + `flutter analyze` + `flutter test`

## Estructura de carpetas clave

```
backend/app/
  core/          # storage.py, security.py, config.py
  domain/        # disease_rules, agronomic_decision, campaign_*, irrigation_intelligence, farm_operation_center, activity_timeline
  connectors/    # aemet_client, ria_ifapa_client, mapa_catalog
  jobs/          # risk_recalculation_job, weather_ingestion_job
  notifications/ # fcm_dispatcher
  main.py        # Rutas FastAPI
  schemas.py     # Modelos Pydantic v2

lib/src/
  core/          # ads, network, notifications, storage, theme, location, privacy
  features/      # auth, parcels, alerts, campaigns, irrigation, operation_center, activity_timeline, agronomic_decision, reports, devices, products, settings, campaign_results
  app.dart       # GoRouter + AppShell (NavigationBar/NavigationRail adaptativo)
  main.dart      # Inicialización resiliente de servicios
```

## Verificación rápida antes de commit

```bash
PYTHONPATH=backend python -m pytest backend/tests -q
flutter analyze
flutter test
```
