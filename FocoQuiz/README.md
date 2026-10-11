# FocoQuiz v0.6 · Android

FocoQuiz es una aplicación Android separada de Memora, alojada en este mismo repositorio **ESTUDIO**.

## Obtener la APK

GitHub → **Actions** → **FocoQuiz · Compilar APK Android** → último flujo correcto → **Artifacts** → **FocoQuiz-v0.6-debug-APK**.

La APK de prueba no está firmada para publicación en Play Store, solo para instalación de prueba.

## Código fuente

El proyecto Android completo está versionado en `FocoQuiz/source-v0.6.tar.xz.base64` para preservar el código Kotlin, Gradle y los recursos de FocoQuiz sin tocar `memora_upgrade/`.

En GitHub Actions, la tarea comprueba la integridad SHA-256 del archivo decodificado, lo descomprime dentro de `FocoQuiz/` y ejecuta `gradle :app:assembleDebug` con Android SDK 35 y Java 17.

Si deseas explorarlo localmente:

```bash
base64 --decode FocoQuiz/source-v0.6.tar.xz.base64 > /tmp/focoquiz.tar.xz
tar -xJf /tmp/focoquiz.tar.xz -C FocoQuiz
cd FocoQuiz
gradle :app:assembleDebug
```

La APK todavía requiere una compilación correcta en GitHub Actions y pruebas en un teléfono Android. Ningún cambio en este directorio debe romper la construcción de Memora.
