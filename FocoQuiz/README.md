# FocoQuiz v0.6.1 · Android

FocoQuiz es una aplicación Android separada de Memora, alojada en este mismo repositorio **ESTUDIO**.

## Obtener la APK

GitHub → **Actions** → **FocoQuiz · Compilar APK Android** → último flujo correcto → **Artifacts** → **FocoQuiz-v0.6.1-debug-APK**.

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

## Cómo importar exámenes de IA externa (solución al aviso «No se pudo importar»)

- **`plantilla_prompt_ia.md` no es un examen**: contiene el prompt para ChatGPT, Gemini, Claude u otra IA.
- Comparte ese `.md` y tu guía con la IA; pide que responda con un archivo `examen.json` que siga `focoquiz.quiz` versión 1.
- En FocoQuiz usa **Banco de preguntas → Importar examen generado por IA (.json)** y selecciona ese `examen.json`, no la plantilla.
- Para comprobar la importación sin usar IA, usa **Probar con examen de ejemplo incluido**.

La actualización 0.6.1 diferencia la plantilla del examen y ofrece instrucciones detalladas cuando se elige un `.md` por error. Instalar una APK anterior a 0.6.1 seguirá mostrando el mensaje antiguo. Es una APK de prueba y no una versión validada en dispositivos reales.

## FocoQuiz v0.6.2 — lectura ampliada

La pantalla **Banco de preguntas** muestra ahora los pasos 1, 2 y 3 como tarjetas independientes, cada una con su botón inmediatamente debajo. Incluye preferencias persistentes **Texto grande** y **Alto contraste**, y todos los botones y etiquetas ganan legibilidad. La prueba de ejemplo se presenta por separado. Ejecutar el workflow `focoquiz-apk.yml` para compilar la APK de Android.

## FocoQuiz v0.6.3 — legibilidad y Accesibilidad

En Configuración general, las listas de preguntas y minutos tienen ahora texto claro sobre fondos oscuros, con opciones desplegadas de alto contraste. También se respetan los bordes seguros de pantalla para que el encabezado no quede oculto por la barra de estado.

Si Android bloquea el servicio, abre **Ayuda: permitir Accesibilidad en Samsung**. FocoQuiz muestra las instrucciones oficiales para **Ajustes > Aplicaciones > FocoQuiz > ⋮ > Permitir ajustes restringidos** (cuando Android ofrece esa opción). El permiso solo puede concederlo el usuario, no la app.

Para preservar los exámenes, actualiza sobre la versión anterior; no desinstales sin antes guardar los datos.
