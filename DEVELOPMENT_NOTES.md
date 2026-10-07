# Notas de desarrollo

## Estado

AgroAlerta Andalucia es una aplicación Flutter responsive con backend FastAPI para avisos fitosanitarios en olivar y vinedo. El cliente está preparado para Android, iOS y Web; el backend concentra las fuentes externas y el cálculo de riesgo.

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
- Gráfica Flutter de evolución del riesgo en el detalle de alerta, conectada a snapshots reales con fallback demo.
- Fixture de pruebas que limpia SQLite entre casos para evitar contaminación de datos.
- Prueba de regresión que garantiza deduplicación de snapshots repetidos.
- Prueba de salud que confirma que no se exponen credenciales de integraciones.
- Prueba de contrato para paginación de historial.

## Decisiones técnicas

- `SharedPreferences` funciona como caché inicial multiplataforma para no bloquear Web. Puede sustituirse por Isar cuando se cierre la estrategia Web.
- Los datos meteorológicos y MAPA siguen teniendo fallback demo hasta validar credenciales, límites y contratos públicos.
- AdMob se muestra solo en pantallas generales; nunca en alertas o recomendaciones fitosanitarias.
- La publicidad requiere consentimiento persistente y revocable.
- Las fotografías deben pasar por Firebase Storage; no se deben enviar rutas locales al backend en producción.
- Las recomendaciones son orientativas y deben conservar trazabilidad de fuente MAPA.
- Los tokens de usuario deben verificarse en backend antes de producción y cada parcela debe filtrarse por propietario.

## Pendientes de producción

1. Ejecutar `flutterfire configure` y añadir configuración Firebase para Android, iOS y Web.
2. Crear los proyectos y credenciales reales de AdMob.
3. Verificar Firebase Storage Rules y Firebase Auth providers.
4. Sustituir SQLite por PostgreSQL/PostGIS en despliegue.
5. Conectar métricas a almacenamiento o Prometheus y panel Flutter de salud.
6. Conectar datos horarios reales de RIA/IFAPA.
7. Verificar mecanismo de exportación o indexación legal del registro MAPA.
8. Añadir métricas de retención y carga incremental en la gráfica Flutter.
9. Configurar permisos nativos de cámara, ubicación, notificaciones y AdMob.
10. Ejecutar `flutter analyze`, `flutter test`, pruebas backend y pruebas en Android, iOS y Web.

## Registro de cambios automatizados

- 2026-10-08: ChatGPT corrigió el aislamiento del estado Riverpod por sesión Firebase y mejoró el diagnóstico de errores de autenticación. El detalle completo está en `docs/AI_CHANGELOG.md`.

## Última validación

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
- Las advertencias actuales proceden de compatibilidad futura entre Starlette y Python 3.14.

## Comandos previstos

```bash
python -m pip install -r backend/requirements.txt
PYTHONPATH=backend python -m pytest backend/tests -q
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```
