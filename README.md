# AgroAlerta Andalucia

MVP multiplataforma para avisos fitosanitarios en olivar y vinedo. El cliente Flutter es responsive y queda preparado para Android, iOS y Web; el backend FastAPI concentra la integracion con fuentes agronomicas.

## Estado actual

Incluye un vertical slice funcional:

- Cliente Flutter con dashboard, parcelas, avisos, productos y ajustes.
- Inicio de sesión obligatorio con Firebase Auth, Google, Apple y correo.
- Parcelas guardadas localmente por `uid` en el dispositivo para funcionamiento offline.
- Publicidad AdMob en pantallas generales, nunca dentro de avisos de enfermedad.
- Navegacion adaptativa: `NavigationBar` en movil y `NavigationRail` en tablet/escritorio.
- Backend FastAPI con parcelas, clima demo, riesgo de repilo/mildiu, productos y reportes.
- Historial de riesgo recuperable desde Flutter para gráficas por parcela.
- Persistencia SQLite local para parcelas y reportes, con CRUD completo.
- Conectores aislados para AEMET y RIA/IFAPA, más importador CSV versionado para MAPA.
- Tarea de ingesta preparada para ejecutarse desde cron, Celery o Cloud Run Jobs.
- Motor de riesgo MVP determinista con respuesta trazable y nivel de confianza estimado.
- Modo demo en la interfaz para revisar la experiencia sin credenciales ni backend.
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

Los datos meteorológicos y MAPA visibles en el MVP son de demostración. Los conectores ya están aislados, pero la activación productiva requiere credenciales de AEMET y verificación de los contratos públicos de RIA y MAPA.

Las recomendaciones no sustituyen la etiqueta oficial ni el asesoramiento de un técnico agrícola.

## Integración continua

Cada push y pull request ejecuta las pruebas FastAPI y el análisis, dependencias y pruebas de Flutter mediante GitHub Actions. Las credenciales se configuran como secretos del entorno de despliegue y nunca se guardan en el repositorio.

## Documentación técnica

La fuente de verdad de la evolución agronómica y de sus contratos es docs/PROJECT_LEDGER.md.

Ese documento registra:
- módulos y responsabilidades;
- tablas y persistencia;
- endpoints;
- reglas de negocio;
- decisiones de diseño;
- pruebas existentes;
- límites conocidos;
- historial de PR #1 a PR #10;
- estado de integración y criterio de cierre.

La arquitectura funcional consolidada es:

Parcela → Riesgo → Decisión → Campaña → Actividades → Resultado productivo
