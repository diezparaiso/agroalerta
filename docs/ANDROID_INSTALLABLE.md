# Android instalable

## Objetivo

El proyecto Flutter todavía no versiona una plataforma Android generada. Para evitar introducir archivos nativos generados sin validación, la primera distribución instalable se construye de forma reproducible en GitHub Actions.

## Artefacto actual

El workflow `.github/workflows/android-apk.yml`:

1. obtiene el código de la rama de desarrollo;
2. genera la plataforma Android con `flutter create --platforms=android`;
3. instala dependencias;
4. ejecuta `flutter analyze`;
5. ejecuta `flutter test`;
6. genera `app-debug.apk`;
7. habilita core library desugaring requerido por las notificaciones locales;\n8. publica el APK como artefacto descargable de GitHub Actions.

El APK debug está firmado con la configuración de depuración generada por Android/Gradle y es apropiado para instalar y probar la aplicación en un dispositivo Android.

## Limitación importante

Este artefacto **no es todavía una distribución de producción**.

Para producción quedan pendientes:

- identificador de aplicación Android definitivo;
- configuración Firebase Android (`google-services.json`) para los servicios que lo requieran;
- App ID nativo de AdMob;
- keystore de firma de producción;
- configuración de secretos de firma en GitHub;
- `flutter build apk --release` o App Bundle firmado;
- validación en dispositivos Android reales.

No se deben introducir claves privadas ni keystores en el repositorio.

## Instalación de la build de pruebas

Desde GitHub Actions se descarga el artefacto `agroalerta-debug-apk`. El archivo resultante es `app-debug.apk`.

En un dispositivo Android de pruebas puede instalarse después de permitir la instalación de aplicaciones procedentes de la fuente utilizada para transferir el APK.

## Criterio de terminado

No consideramos "Android listo para producción" hasta disponer de una build release firmada, configuración nativa de Firebase/AdMob, pruebas en dispositivo y un proceso de distribución reproducible.


## Última validación exitosa

- Workflow: `AgroAlerta Android APK`
- Run: `36442541725`
- Commit: `2a0e2c4422648e4706653bf4972d23096ca46a07`
- Artefacto: `agroalerta-debug-apk`
- APK generado: `app-debug.apk`
- SHA-256 del artefacto de Actions: `8cfb1a6719eac81bd34c237b1adb65374834c19bef9fc99f23fe04f283cf7ee6`
- El artefacto de Actions tiene caducidad configurada a 14 días.

Esta validación demuestra que la aplicación compila y empaqueta como APK Android instalable de depuración. No equivale a una release firmada para distribución pública.
