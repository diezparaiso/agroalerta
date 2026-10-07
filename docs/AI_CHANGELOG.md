# Registro de cambios realizados por ChatGPT

## 2026-10-08 — Aislamiento de sesión y diagnóstico de autenticación

Estos cambios fueron realizados por ChatGPT directamente sobre la rama `fix/user-scoped-riverpod-state`.

### Archivos modificados

- `lib/src/features/parcels/parcel_provider.dart`
  - Añadido `authUserProvider` basado en `FirebaseAuth.instance.authStateChanges()`.
  - `parcelsProvider` ahora depende reactivamente de la sesión Firebase.
  - Al cerrar sesión no reutiliza la caché de `offline-user` ni la del usuario anterior.
  - La caché local continúa estando separada por UID.

- `lib/src/features/alerts/alerts_provider.dart`
  - Se fuerza dependencia de la sesión Firebase para que las alertas no queden cacheadas entre cuentas.

- `lib/src/features/auth/login_screen.dart`
  - Las excepciones de Firebase Auth dejan de ocultarse detrás de un mensaje genérico.
  - Se muestran mensajes accionables para credenciales incorrectas, correo ya usado, contraseña débil, proveedor deshabilitado, red y otros códigos de Firebase.

### Otros archivos modificados

- `DEVELOPMENT_NOTES.md`
  - Añadido el enlace al registro de cambios realizado por ChatGPT.

### Archivos revisados pero no modificados

- `lib/src/features/parcels/parcels_screen.dart`
- `lib/src/features/parcels/parcel_map_preview.dart`
- `lib/src/features/home/weather_provider.dart`
- `lib/src/features/home/telemetry_provider.dart`
- `lib/src/features/reports/report_screen.dart`

- `backend/app/main.py`
- `backend/app/core/security.py`
- `backend/app/core/storage.py`
- `backend/tests/test_api.py`
- `lib/src/features/parcels/local_parcel_store.dart`
- `lib/src/core/network/api_client.dart`

Conclusión del diagnóstico: el backend ya filtra las parcelas por `owner_id` y el cliente ya guarda la caché por UID; el defecto principal estaba en el estado cacheado de los proveedores Riverpod, que no dependían de los cambios de sesión.

> Nota: la configuración Firebase generada localmente por FlutterFire no está actualmente en este repositorio. No se ha inventado ni sustituido ese archivo; la configuración existente en el entorno local debe mantenerse o incorporarse de forma explícita.


## 2026-10-08 — Corrección tras `flutter analyze`

Estos cambios fueron realizados por ChatGPT directamente sobre la rama `feature/complete-agronomic-workflows`.

- `lib/src/features/alerts/alerts_provider.dart`: añadido `parcelId` opcional a `AlertSummary` y conservado desde `parcel_id` en `fromJson`. Esto corrige los errores de `alerts_screen.dart` y del test responsive.
- `lib/src/features/parcels/parcel_map_preview.dart`: eliminadas comprobaciones/aserciones de nulabilidad imposibles sobre coordenadas `double` no nulas.
- `lib/src/features/reports/report_screen.dart`: eliminada la comprobación imposible de nulabilidad de las coordenadas de la parcela.

