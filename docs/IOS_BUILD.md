# Compilación de iOS — guía para Mac

> **MODIFICADO POR OPENCODE** — creado en la Fase 1 (2026-10-05).

## Aviso: iOS no se ha podido compilar desde Windows

**Este proyecto NO se ha podido compilar para iOS en la máquina de desarrollo (Windows 10).** Xcode, los `xcodebuild` y el simulador solo existen en macOS, y Flutter no ofrece compilación iOS cruzada desde Windows. Lo que sí se ha hecho desde Windows en la Fase 1:

- Generación del proyecto iOS con `flutter create --platforms=web,ios --project-name agroalerta_andalucia --org com.example .`
- Claves de permisos en `ios/Runner/Info.plist` (textos en español, ver sección siguiente).
- Verificación de que `git status` no modificó `lib/`, `android/` ni `pubspec.yaml`.

Todo lo demás (pods, firma, compilación, pruebas en simulador/dispositivo) **debe ejecutarse en un Mac**. Esta guía lista los pasos exactos.

## 1. Requisitos en el Mac

1. macOS actualizado y **Xcode** desde el App Store (≥ 16).
2. `xcode-select --install` para las herramientas de línea de comandos.
3. CocoaPods: `sudo gem install cocoapods` (o `brew install cocoapods`).
4. Flutter en la misma versión que este proyecto: **Flutter 3.47.1 stable / Dart 3.13.1**.
5. Una cuenta **Apple Developer** (de pago) si se quiere firmar para dispositivo o TestFlight.

## 2. Compilación mínima sin firma (verificación técnica)

```bash
flutter pub get
cd ios && pod install && cd ..
flutter build ios --debug --no-codesign
```

Este comando **no requiere certificados** y sirve para comprobar que el proyecto, los plugins y el código Dart compilan para iPhone/iPad. Es la primera verificación a ejecutar en el Mac.

Para probar en simulador:

```bash
flutter run -d ios
```

## 3. Firma para dispositivo real o distribución

1. Abrir `ios/Runner.xcworkspace` en Xcode (**no** el `.xcodeproj`).
2. Seleccionar target **Runner** → pestaña *Signing & Capabilities*.
3. Activar *Automatically manage signing* y seleccionar el **Team** de la cuenta Apple Developer.
4. Cambiar el Bundle Identifier actual `com.example.agroalertaAndalucia` por uno propio.
   ⚠️ **Pendiente de decisión del usuario**: el identificador `com.example.*` no es publicable. Lo mismo ocurre con el `applicationId` de Android (`com.example.agroalerta_andalucia`). No se cambia sin aprobación.
5. Compilar para dispositivo: `flutter build ipa --release` (genera el `.xcarchive` para TestFlight/App Store).

## 4. Firebase (obligatorio para Auth, Storage y FCM)

La app arranca sin Firebase (modo anónimo/offline), pero el inicio de sesión real lo requiere.

1. Con credenciales de Firebase, ejecutar en el Mac desde la raíz del proyecto:
   ```bash
   dart pub global activate flutterfire_cli
   flutterfire configure --platforms=ios
   ```
   Esto genera `lib/firebase_options.dart` y `ios/Runner/GoogleService-Info.plist`.
2. Añadir `GoogleService-Info.plist` al target **Runner** arrastrándolo en Xcode (opción *Copy items if needed*).
3. Ajustar `lib/main.dart` para pasar las opciones: `Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform)`. **Solo se hace cuando exista el archivo**; no se simula configuración.
4. En Firebase Console: activar proveedores (correo, Google, Apple) y descargar el `GoogleService-Info.plist` si no se usa `flutterfire`.
5. **No hacer commit** de claves de servicio; `GoogleService-Info.plist` no contiene secretos de servidor pero conviene decidir con el usuario si se versiona.

> `lib/firebase_options.dart` **no existe todavía**: marcador pendiente. Mientras tanto, en iOS la app funciona en modo local sin sesión (mismo comportamiento que hoy en Android).

## 5. Capacidades que NO se han añadido (requieren certificados)

Estas capacidades se omiten a propósito hasta que existan las credenciales. Añadirlas sin ellas rompe la compilación o el arranque:

| Capacidad | Requisito | Dónde |
|---|---|---|
| *Push Notifications* | Certificado APNs (llave `.p8` o certificado `.cer`) y Apple Developer | Xcode → *Signing & Capabilities* → *+ Capability* |
| *Sign in with Apple* | Apple Developer con la capability habilitada para el Bundle ID | Xcode → *Signing & Capabilities* |
| *Background Modes → Remote notifications* | Solo con Firebase Cloud Messaging configurado | Xcode → *Signing & Capabilities* |

Pasos cuando existan credenciales (decisión del usuario):

1. Subir la **llave Auth Key `.p8`** de APNs a Firebase Console → *Cloud Messaging*.
2. Activar *Push Notifications* y *Background Modes → Remote notifications* en Xcode.
3. Compilar en dispositivo físico y verificar la recepción de tokens FCM (el backend ya persiste tokens con `POST /api/v1/push-tokens`).

Para **Sign in with Apple** además hay que activar la capability en el panel de Apple Developer para el Bundle ID definitivo. La app ya incluye `sign_in_with_apple` en el código, pero el botón solo funcionará cuando exista la capability: hoy devuelve un error controlado.

## 6. AdMob (iOS)

Antes de distribuir con anuncios reales:

1. Obtener el **ID real de AdMob** (pendiente del usuario) y sustituir el ID de prueba por `--dart-define=ADMOB_BANNER_ID=...` en build de release.
2. Añadir a `ios/Runner/Info.plist`:
   - `GADApplicationIdentifier` con el ID de aplicación de AdMob (`ca-app-pub-xxxxxxxx~yyyyyyyy`).
   - `NSUserTrackingUsageDescription` solo si se activa la atribución (decisión de producto/privacidad → preguntar).
3. Añadir el `SKAdNetworkItems` con los IDs de AdMob. **No se versionan IDs falsos**: estos valores los aporta el usuario cuando tenga cuenta.

Los anuncios están tras importación condicional (`core/ads/`), de modo que un build sin ID funciona: simplemente no muestra banner.

## 7. Permisos ya declarados en `Info.plist` (Fase 1)

| Clave | Texto | Uso en el código |
|---|---|---|
| `NSLocationWhenInUseUsageDescription` | "AgroAlerta usa tu ubicación para situar la parcela en el mapa y calcular el riesgo de tu zona. Puedes negarte y escribir las coordenadas a mano." | `core/location/location_service.dart` (geolocator) |
| `NSCameraUsageDescription` | "AgroAlerta usa la cámara para fotografiar síntomas de enfermedades o trampas en el campo y adjuntarlas a un informe." | `features/reports/report_screen.dart` (image_picker) |
| `NSPhotoLibraryUsageDescription` | "AgroAlerta accede a tu galería para adjuntar fotografías de campo a un informe." | image_picker (galería) |

Las **notificaciones locales** no requieren clave en `Info.plist`: el permiso se pide en tiempo de ejecución (`IOSFlutterLocalNotificationsPlugin.requestPermissions`, ya en el código). Las **notificaciones remotas** sí requieren la capability de la sección 5.

Si se añade subida de fotos desde la galería de otra forma, revisar que `NSPhotoLibraryUsageDescription` siga siendo suficiente.

## 8. Lista de verificación en el Mac

- [ ] `flutter pub get` sin errores.
- [ ] `cd ios && pod install` sin errores.
- [ ] `flutter build ios --debug --no-codesign` compila.
- [ ] `flutter run -d ios` (simulador) arranca sin excepciones y la app llega a `/home`.
- [ ] Permiso de ubicación: formulario de parcela → GPS → diálogo en español con el texto de `NSLocationWhenInUseUsageDescription`.
- [ ] Cámara en observación de campo → diálogo de permiso en español.
- [ ] Firebase: `flutterfire configure` + login con correo/Google/Apple (Apple solo con capability).
- [ ] Firma automática con Team propio y Bundle ID definitivo (pendiente del usuario).
- [ ] Push (opcional, con llave `.p8`): token FCM registrado y `POST /api/v1/push-tokens` responde 202.
- [ ] AdMob con ID real (pendiente del usuario) o sin banner si no se configura.

## 9. Qué queda en manos del usuario

1. Cuenta Apple Developer y Team de firma.
2. Bundle ID definitivo (sustituir `com.example.agroalertaAndalucia`).
3. Proyecto Firebase y `flutterfire configure` (GoogleService-Info.plist).
4. Llave `.p8` de APNs si se quiere push.
5. Capability *Sign in with Apple* activada en Apple Developer.
6. IDs reales de AdMob.
7. Prueba física en iPhone (simulador no cubre permisos de notificación/push reales).
