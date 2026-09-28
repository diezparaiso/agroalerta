# AgroAlerta Andalucia

MVP multiplataforma para avisos fitosanitarios en olivar y vinedo. El cliente Flutter es responsive y queda preparado para Android, iOS y Web; el backend FastAPI concentra la integracion con fuentes agronomicas.

## Estado actual

Incluye un vertical slice funcional:

- Cliente Flutter con dashboard, parcelas, avisos, productos y ajustes.
- Inicio de sesión obligatorio con Firebase Auth, Google, Apple y correo.
- Parcelas guardadas localmente por `uid` en el dispositivo para funcionamiento offline.
- Publicidad AdMob en pantallas generales, nunca dentro de avisos de enfermedad.
- Navegacion adaptativa: `NavigationBar` en movil y `NavigationRail` en tablet/escritorio.
- Backend FastAPI con parcelas, meteorología persistida, riesgo de repilo/mildiu, productos y reportes.
- Historial de riesgo recuperable desde Flutter para gráficas por parcela.
- Persistencia SQLite local para parcelas y reportes, con CRUD completo.
- Conectores aislados para AEMET y RIA/IFAPA, más importador CSV versionado para MAPA.
- Tarea de ingesta preparada para ejecutarse desde cron, Celery o Cloud Run Jobs.
- Motor de riesgo MVP determinista con respuesta trazable y nivel de confianza estimado.
- Configuracion de VS Code, Docker Compose y pruebas del backend.

## Ejecutar el backend

```bash
python -m pip install -r backend/requirements.txt
PYTHONPATH=backend python -m pytest backend/tests -q
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

Alternativamente:

```bash
docker compose up --build
```

La documentacion OpenAPI queda disponible en `http://localhost:8000/docs`.

## Ejecutar Flutter en el PC

Con Flutter instalado:

```bash
flutter pub get
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

Para Android o iOS se mantiene el mismo codigo y se cambia únicamente el dispositivo de ejecución. Hay que añadir los archivos de configuración de Firebase (`google-services.json` y `GoogleService-Info.plist`) y activar los proveedores Google, Apple y correo en Firebase Console.

AdMob utiliza IDs de prueba por defecto. En una compilación de distribución se debe proporcionar el ID real:

```bash
flutter run -d android --dart-define=ADMOB_BANNER_ID=ca-app-pub-xxxxxxxxxxxxxxxx/xxxxxxxxxx
```

También hay que registrar el `APPLICATION_ID` de AdMob en Android y el `GADApplicationIdentifier` en `Info.plist` para iOS. Web no muestra anuncios todavía; se reserva para una integración publicitaria web independiente.

## Decisiones del MVP

El almacenamiento local del cliente usa `shared_preferences` como adaptador multiplataforma inicial para evitar bloquear Web. La interfaz `OfflineCache` permite sustituirlo por Isar cuando se confirme la estrategia de soporte Web. El backend persiste sus datos de desarrollo en `backend/agroalerta.db` y puede migrarse a PostgreSQL/PostGIS sin cambiar los contratos HTTP.

La interfaz no presenta datos agronómicos ficticios como si fueran observaciones reales. Cuando falta evidencia meteorológica, se muestra explícitamente como no disponible. Los conectores externos siguen requiriendo validación de contratos, credenciales cuando proceda y configuración productiva.

Las recomendaciones no sustituyen la etiqueta oficial ni el asesoramiento de un técnico agrícola.

## Integración continua

Cada push y pull request ejecuta las pruebas FastAPI y el análisis, dependencias y pruebas de Flutter mediante GitHub Actions. Las credenciales se configuran como secretos del entorno de despliegue y nunca se guardan en el repositorio.
## Capa de datos agronomicos

Se ha añadido un catalogo interno de fuentes en `backend/app/connectors/source_registry.py` y el endpoint `GET /api/v1/data-sources`. El catalogo separa la procedencia de los datos del motor agronomico.

Fuentes priorizadas: RAIF fitosanitario, RAIF clima, RIA/IFAPA, AEMET, SIGPAC, IDEAndalucia/DERA y catalogo oficial de productos fitosanitarios.

La arquitectura y el estado de validacion de cada fuente quedan documentados en `docs/FUENTES_DATOS_OFICIALES.md`.

La tarea de ingesta meteorologica ya no utiliza una ventana fija 2026/01-12: por defecto trabaja con el mes UTC actual y permite recibir una ventana explicita desde el scheduler.

## Ingeniería y buenas prácticas

Las decisiones de arquitectura y las reglas que deben acompañar cada cambio están documentadas en docs/DECISIONS.md y docs/ENGINEERING_GUIDELINES.md. Estos documentos forman parte del criterio de terminado del proyecto: los cambios relevantes deben dejar constancia de intención, impacto, validación y decisiones técnicas.

## Estado de ingeniería

La cobertura funcional estimada por módulos, su metodología y los pendientes de producción se mantienen en [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md). Es una estimación de ingeniería, no una métrica de líneas de código.
