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

## FocoQuiz 0.6.4 — evitar que parpadee la pantalla de examen

Se corrigió la detección de ventanas del servicio de Accesibilidad. Las notificaciones de ventana emitidas por la superposición de bloqueo no deben cerrar el cuestionario. Solo al abrir una pantalla real de FocoQuiz o una aplicación esencial se retira la superposición. Se incluye prueba de regresión en `tests/ForegroundWindowEventsSmoke.kt`.

Esta versión necesita validación en un teléfono Android con servicio de Accesibilidad habilitado. Conserva las preguntas, horarios y planes guardados si el sistema permite actualizar la aplicación sin desinstalar.

## FocoQuiz 0.6.5 — navegación y teclado del cuestionario

La pantalla del examen se coloca arriba para que el teclado no oculte los botones. Se retira `FLAG_LAYOUT_IN_SCREEN` para respetar las barras de navegación de Android y se ajusta la ventana a la barra de estado, la barra de navegación y el teclado. El cuestionario tiene un botón visible para **Ocultar teclado** y otro para **Ir al inicio sin desbloquear**, de forma que FocoQuiz no impide usar las funciones esenciales del teléfono. El teclado deja de abrirse automáticamente y puede cerrarse con la tecla «Listo».

Requiere probarlo en Samsung One UI/Android 16, puesto que la gestión de ventanas de Accesibilidad e IME depende del fabricante y de la versión del sistema.

## Firma estable (nueva forma de distribuir FocoQuiz)

En este repositorio publico no se almacena la clave privada de firma. La primera y las futuras APK que se puedan actualizar se generan mediante el flujo **FocoQuiz · APK estable actualizable**, una vez configurados los secretos indicados en [FIRMA_ESTABLE.md](FIRMA_ESTABLE.md). Las APK debug de los otros flujos NO comparten esa clave y deben considerarse solo pruebas. No distribuyas como actualización una APK debug.

## FocoQuiz v0.6.6 — APK actualizable con una misma firma

Las APK anteriores de GitHub Actions tenían firmas de depuración distintas y Android exigía desinstalar.
Desde esta versión se usa una firma privada persistente **solo para compilaciones release** lanzadas manualmente en la rama `main`.
No guardes la contraseña ni el fichero de firma como código público.

Preparación única:
1. Conserva fuera de GitHub el archivo privado `FocoQuiz-FIRMA-PRIVADA.zip` que contiene una clave cifrada y dos textos para secretos.
2. En el repositorio: **Settings → Secrets and variables → Actions → New repository secret**.
3. Crea exactamente `FOCOQUIZ_SIGNING_KEYSTORE_BASE64` con el contenido de `FOCOQUIZ_SIGNING_KEYSTORE_BASE64.txt`.
4. Crea exactamente `FOCOQUIZ_SIGNING_PASSWORD` con el contenido de `FOCOQUIZ_SIGNING_PASSWORD.txt`.
5. En **Actions → FocoQuiz · Compilar APK Android → Run workflow**, selecciona `main`.
6. Descarga el artefacto `FocoQuiz-v0.6.6-release-APK-firma-permanente`.

La clave de firma solo existe en los secretos de GitHub (y en el respaldo privado). Los commits y PRs compilan una APK de prueba sin publicar artefactos actualizables.
Sin secretos el paso de publicación falla de forma deliberada, para no generar APKs con otra firma por accidente.

Antes de instalar la primera v0.6.6 release, **desinstala UNA vez** tu APK v0.6.5 o anterior (se perderán sus datos); ya indicaste que no hace falta conservarlos.
Desde entonces mantén estos secretos y aumenta `versionCode` en cada versión: las nuevas APK release permitirán actualizar sin desinstalar.

## FocoQuiz 0.6.7 — apertura rápida

La pantalla principal no espera a la lectura de aplicaciones instaladas ni a la reprogramación de alarmas al abrir. Estas tareas, junto con la carga de iconos, se realizan en segundo plano. Para evitar demoras al crear una lista enorme, se muestran inicialmente 24 aplicaciones con el botón **Mostrar más aplicaciones** y un buscador con breve espera. El servicio de Accesibilidad sigue funcionando independientemente. La compilación release conserva los secretos de firma permanente configurados para las futuras actualizaciones sin desinstalar.

## FocoQuiz v0.6.8 — inicio fluido y alarmas más eficientes

Se añade una memoria caché temporal de iconos de las aplicaciones para no descodificarlos en cada regreso a la pantalla. Al iniciar, FocoQuiz evita cancelar/reprogramar todas las alarmas si lo hizo hace menos de una hora. Las modificaciones de planes de estudio y los eventos de reinicio/cambio de hora siguen actualizando las alarmas inmediatamente. Es una APK release con el mismo certificado persistente y `versionCode` superior para actualizar encima de 0.6.6 y 0.6.7.

## FocoQuiz v0.6.9 — horario diario para editar la configuración

En la pantalla principal aparece **Horario para configurar FocoQuiz**. Puedes elegir **Hora de inicio** y **Hora de fin**, activar la restricción y pulsar **Guardar horario**. Por seguridad, esta función comienza desactivada hasta que la configures, y no permite elegir inicio y fin idénticos.

Cuando llegue la hora final, la configuración se cierra automáticamente y aparece una pantalla informativa con las horas de acceso permitidas. La restricción se aplica a reglas de apps, preguntas, importación de exámenes, rutinas, planes y al propio horario: **no es posible cambiar el horario fuera de la franja habilitada**. También se comprueba el horario si abres un editor por acceso directo o compartes un examen. Los horarios admiten cruces de medianoche y se aplican todos los días.

**Importante:** el servicio de bloqueo, los retos, el acceso a inicio/atrás de Android y las alarmas de estudio continúan funcionando fuera de las horas de configuración. El horario restringe los **ajustes**, no la navegación normal del dispositivo. Los controles del sistema operativo siguen accesibles y Android permite desactivar el servicio de Accesibilidad desde Ajustes.

Se distribuye como APK release con firma permanente y `versionCode 15`, actualizable sobre la versión 0.6.8.
