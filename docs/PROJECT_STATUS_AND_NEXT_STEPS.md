# AgroAlerta — estado del proyecto y guía de continuidad

> Documento de traspaso técnico. Actualizado el 31/10/2026 durante la integración del laboratorio de conectores RIA-IFAPA y AEMET. La referencia de trabajo es la rama `integration/connector-lab-main` y el PR #18. Este documento describe el estado comprobado; lo que no se ha verificado se identifica expresamente como pendiente.

## 1. Repositorio, rama y reglas de trabajo

- Repositorio: `diezparaiso/agroalerta`.
- Rama de integración: `integration/connector-lab-main`.
- Pull request: [#18 — Integrate connector lab into main for RIA-IFAPA and AEMET testing](https://github.com/diezparaiso/agroalerta/pull/18).
- `main` debe permanecer intacta hasta que el propietario valide la integración.
- No fusionar el PR, desplegar el backend, modificar secretos ni cambiar servicios remotos sin autorización explícita.
- No introducir claves privadas, tokens ni credenciales en Flutter, APK, logs o Git.
- El objetivo inmediato es conseguir una compilación Android reproducible y validar el laboratorio antes de integrar.

## 2. Qué es AgroAlerta

MVP multiplataforma para avisos fitosanitarios en olivar y viñedo. El cliente está desarrollado en Flutter y el backend en FastAPI. La integración de conectores se concentra en el backend para no exponer secretos ni duplicar lógica de acceso a fuentes externas en el cliente.

El README del repositorio describe el MVP general: dashboard, parcelas, avisos, productos, ajustes, autenticación Firebase, almacenamiento local, publicidad AdMob, navegación adaptativa, reportes, dispositivos/telemetría y backend con persistencia SQLite. Parte de la información de clima, productos y riesgo sigue siendo demostrativa; no debe confundirse con una conexión productiva a fuentes oficiales.

## 3. Alcance de esta integración: laboratorio de conectores

Se ha añadido una pantalla Flutter accesible desde **Ajustes → Laboratorio de conectores**, con ruta `/connector-lab`.

La pantalla permite:
- Probar individualmente RIA-IFAPA, AEMET, MAPA y SIGPAC.
- Mostrar el estado de cada conector, mensaje, fecha de consulta, número de registros y campos detectados.
- Consultar y visualizar la respuesta original recibida.
- Copiar los resultados JSON.
- Exportar la respuesta a un libro XLSX con tres hojas: **Datos originales**, **Datos interpretados** e **Información de consulta**.
- Introducir el código INE de municipio para AEMET; el valor inicial es `41091` (Sevilla).

La interfaz distingue explícitamente entre conectado, conectado sin registros, sin configurar, pendiente de implementar y error. No debe etiquetarse un conector como operativo si no se ha recibido una respuesta real.

### 3.1 RIA-IFAPA

Cliente: `backend/app/connectors/ria_ifapa_client.py`.

- Catálogo de estaciones: `GET {RIA_BASE_URL}/estaciones`.
- Datos diarios: `GET {RIA_BASE_URL}/datosdiarios/forceEt0/{province}/{station}/{date_from}/{date_to}`.
- No requiere API key según la integración actual.
- La prueba de laboratorio consulta el catálogo de estaciones. El método de datos diarios existe en el cliente, pero la pantalla actual no ofrece todavía selección de estación, provincia y rango de fechas para probarlo.
- La respuesta del catálogo debe ser una lista JSON; si no lo es, se considera respuesta inválida/error.

### 3.2 AEMET OpenData

Cliente: `backend/app/connectors/aemet_client.py`.

- Consulta de predicción diaria municipal en dos pasos:
  1. Solicitud a `/prediccion/especifica/municipio/diaria/{municipality_code}`, enviando `AEMET_API_KEY` en la cabecera `api_key`.
  2. Lectura de la URL de datos indicada por AEMET en el campo `datos`.
- La clave solo debe existir en el entorno del backend. Flutter no la recibe ni la transmite.
- Si no existe la variable, el estado esperado es `not_configured`, no un falso error de conexión.
- La prueba por defecto utiliza el código INE `41091`; se puede cambiar desde la pantalla.
- Las pruebas automáticas simulan las respuestas y verifican que la clave no aparece en el JSON devuelto. No demuestran por sí mismas que una clave real funcione.

Configuración pendiente para una prueba real:
- Definir `AEMET_API_KEY` como secreto/variable de entorno del servicio backend.
- Reiniciar o desplegar el backend por parte del propietario/operador.
- Ejecutar de nuevo la prueba AEMET y comprobar que devuelve `connected` y datos reales.

No solicitar ni copiar la clave en el chat ni en el repositorio.

### 3.3 MAPA y SIGPAC

- Se muestran en el laboratorio para dejar visible el alcance pendiente.
- El backend devuelve `not_implemented`.
- No existe en esta integración un conector real de consulta directa para MAPA ni SIGPAC.
- No simular que están conectados ni presentar datos demo como respuesta oficial.
- MAPA puede requerir una estrategia de importación/sincronización de catálogo; SIGPAC necesita un diseño de acceso y consulta específico. Deben abordarse como trabajos separados, tras verificar contratos y condiciones oficiales.

## 4. Contrato HTTP del laboratorio

Prefijo: `/api/v1/connector-lab`.

| Método y ruta | Uso |
|---|---|
| `GET /api/v1/connector-lab/ria` | Prueba del catálogo de estaciones RIA-IFAPA |
| `GET /api/v1/connector-lab/aemet?municipality_code=41091` | Prueba AEMET para código INE de cinco dígitos |
| `GET /api/v1/connector-lab/mapa` | Devuelve estado `not_implemented` |
| `GET /api/v1/connector-lab/sigpac` | Devuelve estado `not_implemented` |

Respuesta común del laboratorio:
- `connector`: nombre del proveedor.
- `status`: estado normalizado.
- `configured`: si hay configuración básica disponible.
- `tested_at`: fecha/hora UTC de la consulta.
- `endpoint`: endpoint consultado cuando procede.
- `record_count`: número de elementos o 1 si se recibe un objeto.
- `message`: explicación breve.
- `raw_data`: respuesta original, sin la clave de AEMET.

Estados previstos:
- `connected`: consulta con datos recibidos.
- `empty`: consulta correcta sin registros.
- `not_configured`: falta configuración/credencial.
- `not_implemented`: conector todavía no implementado.
- `error`: fallo de consulta.

El endpoint captura excepciones de los conectores y evita devolver el valor de la clave. Los mensajes de error incluyen el tipo de excepción, no el contenido de credenciales.

## 5. Reintentos y gestión HTTP

Archivo: `backend/app/connectors/http_retry.py`.

- Máximo de tres intentos.
- Reintenta timeouts y respuestas HTTP 429 o 5xx.
- No reintenta errores HTTP no recuperables.
- Respeta `Retry-After` cuando es numérico, con espera limitada a 30 segundos.
- Backoff exponencial inicial de 0,5 segundos.
- Los clientes usan `httpx.AsyncClient` con timeout de 15 segundos y cierran el cliente cuando son propietarios de él.

## 6. Archivos principales afectados

- `.github/workflows/ci.yml`: pipeline backend/Flutter, build web y build APK Android debug.
- `backend/app/api/connector_lab.py`: endpoints y normalización de estados.
- `backend/app/connectors/aemet_client.py`: cliente AEMET.
- `backend/app/connectors/ria_ifapa_client.py`: cliente RIA-IFAPA.
- `backend/app/connectors/http_retry.py`: reintentos HTTP.
- `backend/app/main.py`: registro del router del laboratorio.
- `backend/tests/test_connector_lab.py`: tests del laboratorio.
- `lib/src/core/network/api_client.dart`: llamada Flutter al backend.
- `lib/src/features/settings/connector_lab_screen.dart`: interfaz, resultados y exportación XLSX.
- `lib/src/features/settings/settings_screen.dart`: acceso desde Ajustes.
- `lib/src/app.dart`: ruta `/connector-lab`.
- `pubspec.yaml`: dependencias `excel` y `file_saver`, entre otras.
- `docs/CONNECTOR_LAB.md`: guía funcional resumida del laboratorio.

La lista completa de ficheros modificados se encuentra en el PR #18.

## 7. Cómo ejecutar y probar el proyecto

### 7.1 Backend local

Desde la raíz del repositorio:

```powershell
python -m pip install -r backend/requirements.txt
$env:PYTHONPATH = "backend"
python -m pytest backend/tests -q
python -m uvicorn app.main:app --reload --port 8000
```

Documentación OpenAPI local: `http://localhost:8000/docs`.

Comprobar endpoints:
- `http://localhost:8000/health`
- `http://localhost:8000/health/integrations`
- `http://localhost:8000/api/v1/connector-lab/ria`
- `http://localhost:8000/api/v1/connector-lab/aemet?municipality_code=41091`

Para una prueba real de AEMET, la variable `AEMET_API_KEY` debe estar configurada en el proceso backend antes de arrancarlo.

### 7.2 Flutter

```powershell
flutter pub get
flutter analyze
flutter test
```

La URL base se configura con `API_BASE_URL`. El valor por defecto del cliente es `http://localhost:8000`, que solo es apropiado cuando el backend es accesible desde el dispositivo que ejecuta Flutter. Para Android físico/emulador hay que indicar una URL de backend alcanzable desde ese dispositivo.

Ejemplo:

```powershell
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

### 7.3 Android

Comando esperado para APK de depuración:

```powershell
flutter build apk --debug
```

Ruta de salida esperada:

```text
build/app/outputs/flutter-apk/app-debug.apk
```

La mera existencia de una carpeta `build` o de un artefacto Web no acredita que se haya generado el APK. Comprobar el fichero y su tamaño/fecha tras una compilación que termine correctamente.

## 8. Estado comprobado de CI y Android a 31/10/2026

### 8.1 GitHub Actions

Último run de CI analizado durante esta sesión:
- Run ID: `41191399706`.
- Commit probado: `fa5d4be000a7637df8ed37a21689ea3ae9694eb0`.
- Resultado global: **failure**.
- Job backend: success.
- Flutter analyze/tests: success.
- Flutter Web release: success.
- Generación del scaffold Android: success.
- Paso de activación de desugaring: aparece como success, pero su script no comprueba que haya insertado realmente la dependencia.
- Build APK Android debug: failure.
- Upload del APK: omitido porque el build falló.
- Artefacto Web release: sí se generó; no sustituye al APK.

Error de Gradle reportado en ese run:

```text
Could not determine the dependencies of task ':app:packageDebug'.
> Could not create task ':app:l8DexDesugarLibDebug'.
  > coreLibraryDesugaring configuration contains no dependencies.
```

El workflow intentaba insertar `coreLibraryDesugaring(...)` mediante un reemplazo textual de `dependencies {`. Si no encuentra ese bloque, el script no falla ni verifica el cambio: imprime un mensaje de éxito aunque la dependencia no se haya añadido. Esa es una deficiencia conocida del workflow y debe corregirse con una edición/validación robusta del Gradle generado.

### 8.2 Prueba local realizada

En la máquina Windows se cambió a la rama `integration/connector-lab-main`, se generó el scaffold Android porque no existía la carpeta `android`, se aplicó una modificación local de Gradle y se ejecutó `flutter pub get`.

El comando de compilación ejecutado fue:

```powershell
flutter build apk --debug 2>&1 | Tee-Object -FilePath ".\build-apk-local.log"
```

La primera salida comunicó un error de compilación Kotlin DSL en:

```text
android/app/build.gradle.kts:42:1
None of the following candidates is applicable
```

El contenido del archivo local compartido en la conversación incluía:
- `isCoreLibraryDesugaringEnabled = true` dentro de `compileOptions`.
- `coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")` dentro de `dependencies`.
- Un bloque `kotlin { compilerOptions { jvmTarget = ... } }`.

El fragmento de log verbose compartido después contenía principalmente mensajes de caché y advertencias de plugins; terminaba antes de mostrar el diagnóstico final. Por tanto, **la causa exacta del error local aún no está confirmada**. No concluir que las advertencias de AGP/Kotlin sean la causa sin el bloque `FAILURE: Build failed with an exception` y el detalle `What went wrong`.

Importante: el scaffold Android se generó localmente durante esta sesión. No asumir que esos archivos están versionados en la rama: comprobar `git status` y `git check-ignore` antes de decidir cómo incorporarlos.

## 9. Próximas tareas — orden recomendado

### Prioridad 1 — cerrar compilación Android

1. Recuperar el diagnóstico final del log local, no el bloque de transformaciones/caché:
   ```powershell
   Select-String -Path .\build-apk-verbose.log -Pattern "FAILURE:|What went wrong:|Build file |Script compilation error|e: file:|Unresolved reference|None of the following candidates|Could not" -Context 2,6 | Select-Object -Last 60
   ```
2. Revisar el Gradle generado completo: `android/app/build.gradle.kts`, `android/build.gradle.kts`, `android/settings.gradle.kts` y `android/gradle.properties`.
3. Confirmar las versiones efectivas de Flutter, Gradle Wrapper, Android Gradle Plugin y Kotlin; no actualizar versiones a ciegas.
4. Corregir el error de DSL concreto y volver a compilar localmente.
5. Confirmar que existe `build/app/outputs/flutter-apk/app-debug.apk`.
6. Revisar si el scaffold Android debe quedar versionado en esta rama para que la CI no dependa de generarlo de forma efímera.

### Prioridad 2 — reparar CI Android de forma permanente

1. Sustituir el reemplazo textual frágil de `.github/workflows/ci.yml` por una modificación que:
   - localice el archivo Gradle real;
   - inserte la dependencia dentro de un bloque `dependencies` válido o cree el bloque si procede;
   - habilite desugaring en `compileOptions`;
   - compruebe explícitamente que ambas configuraciones están presentes;
   - falle con un mensaje claro si no puede aplicar el cambio.
2. Alinear la versión de `desugar_jdk_libs` con la configuración compatible y validada localmente; no cambiarla sin motivo.
3. Evitar que el paso de build se ejecute con configuración incompleta y que un paso imprima éxito falso.
4. Hacer push solo a `integration/connector-lab-main`, lanzar CI y verificar el artefacto `agroalerta-android-debug-apk`.
5. Solo considerar el APK disponible cuando el job Flutter finalice correctamente y el artefacto exista.

### Prioridad 3 — validación funcional del laboratorio

1. Ejecutar tests backend y Flutter.
2. Arrancar el backend local y comprobar RIA real.
3. Configurar AEMET_API_KEY únicamente como secreto/variable de entorno en el backend de pruebas y comprobar AEMET real.
4. Probar la exportación XLSX y verificar las tres hojas, encabezados y conservación de campos originales.
5. Comprobar que la clave AEMET no aparece en respuestas, archivos XLSX, consola ni logs.
6. Mantener MAPA y SIGPAC como pendientes hasta que existan conectores reales probados.

### Prioridad 4 — revisión antes de integrar

1. Revisar diff completo del PR #18.
2. Verificar documentación, tests, configuración y que no se hayan introducido credenciales.
3. Probar en Android y Web.
4. Presentar resultados al propietario para validación.
5. No fusionar el PR hasta recibir autorización expresa.

## 10. Incidencias y precauciones conocidas

- La prueba CI del APK falló; todavía no hay APK de este proceso confirmada.
- La compilación Web release sí terminó correctamente en el run indicado.
- El build local falló en el script Kotlin DSL, pero falta el diagnóstico final para atribuir la causa.
- La CI actual puede anunciar que habilitó desugaring sin haber insertado la dependencia.
- Las pruebas de AEMET son simuladas mientras no se configure una clave real en el backend.
- La disponibilidad de RIA/AEMET depende de conectividad y de que sus servicios públicos respondan.
- El backend debe ser accesible desde el dispositivo Flutter; `localhost` en un móvil no apunta al PC.
- Los datos demo del resto del MVP no deben presentarse como datos oficiales en producción.
- No desplegar backend, cambiar secretos ni fusionar el PR sin permiso.

## 11. Referencias oficiales

- AEMET OpenData: https://opendata.aemet.es/dist/
- IFAPA — Red de Información Agroclimática de Andalucía: https://www.juntadeandalucia.es/agriculturaypesca/ifapa/web/red-de-informacion-agroclimatica-de-andalucia
- Pull request de integración: https://github.com/diezparaiso/agroalerta/pull/18
- Último run CI analizado: https://github.com/diezparaiso/agroalerta/actions/runs/41191399706

---

## Instrucción para la siguiente sesión de desarrollo

Continuar exclusivamente desde `integration/connector-lab-main`. Leer primero este documento y `docs/CONNECTOR_LAB.md`. La primera tarea es recuperar el error completo de Gradle y cerrar la compilación Android. No empezar nuevas funcionalidades ni alterar `main`, secretos o despliegues. Al finalizar cada bloque de trabajo, actualizar este documento con cambios, pruebas ejecutadas, resultados, commit y tareas pendientes.
