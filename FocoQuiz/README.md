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

## FocoQuiz v0.6.10 — calculadora integrada en el cuestionario

En los cuestionarios de bloqueo y los exámenes de planes de estudio aparece un pequeño botón **▦ Calculadora**. Al pulsarlo se despliega una calculadora dentro de la misma pantalla, sin abrir ventanas adicionales, para evitar parpadeos y conservar el progreso. Permite paréntesis, suma, resta, multiplicación, división, porcentajes y raíz cuadrada, con resultado visible. En las preguntas de respuesta escrita ofrece **Usar resultado en mi respuesta**. En preguntas de opción múltiple sirve para hacer cálculos y luego elegir la opción. Se cierra sin cambiar la pregunta actual.

La APK sigue firmada con la clave permanente y el `versionCode` se eleva a 16 para actualizar sobre v0.6.9 sin desinstalar.

## FocoQuiz v0.6.11 — fórmulas de la guía disponibles durante el examen

Hay un nuevo botón compacto **ƒx Fórmulas** junto al botón Calculadora durante los cuestionarios del bloqueo y los exámenes de los planes de estudio. El botón despliega dentro de la misma pregunta las fórmulas extraídas de la guía, mostrando primero las relacionadas con la pregunta y permitiendo consultar las demás sin salir de FocoQuiz. Funciona sin Internet y sin nuevas ventanas flotantes que puedan provocar parpadeos.

El prompt universal y el ejemplo, descargables en **Banco de preguntas**, incluyen dos campos opcionales compatibles con el formato `focoquiz.quiz` versión 1:
- `formulas`: array en la raíz con elementos `id`, `name`, `expression`, `variables`, `when_to_use` y `topic`. Hasta 120 fórmulas; la IA debe extraer exclusivamente fórmulas existentes en la guía, sin inventar contenido ni revelar soluciones particulares.
- `formula_ids`: array de IDs en cada pregunta que indica cuáles fórmulas de la guía aplican a ella. Hasta 20 por pregunta.

Al importar, FocoQuiz guarda las fórmulas una sola vez por examen y las relaciones de cada pregunta, y las presenta completamente offline. Los exámenes antiguos siguen funcionando pero, si no contienen fórmulas, el botón indica que se debe regenerar el JSON con el nuevo prompt.

La nueva APK release mantiene la firma permanente y actualiza el código de versión a 17.

## FocoQuiz v0.6.12 — biblioteca de guías enlazadas, sin copias

En el **dashboard principal** se encuentra **📖 Biblioteca de guías**. Con **Seleccionar guía del teléfono**, el selector de documentos de Android abre el archivo original usando `ACTION_OPEN_DOCUMENT` y FocoQuiz guarda **solo su URI `content://` y el permiso de lectura persistente**, sin duplicar sus bytes. Esto apenas usa almacenamiento: los documentos originales siguen siendo responsabilidad del proveedor del archivo. Si el archivo se mueve, se elimina o el proveedor revoca acceso, hay que seleccionarlo de nuevo. La biblioteca permite abrir y **Quitar de biblioteca**, que elimina únicamente el enlace y nunca borra el archivo original. El alta/baja respeta el horario para editar la configuración.

En la **esquina superior izquierda del cuestionario**, el pequeño botón **📖 Guía** abre la selección de guías existentes. La guía elegida queda recordada por examen; se puede volver al quiz, conservando el progreso incluso en el bloqueo por Accesibilidad. También funciona en los exámenes de planes de estudio.

El lector incorporado abre PDF, TXT/MD e imágenes referenciadas sin copiarlas. En PDF muestra páginas anterior/siguiente y busca palabras o frases con un extractor de texto local; en TXT/MD busca y resalta texto. PDF escaneado e imágenes no permiten búsqueda sin OCR. Formatos que requieran un visor externo se pueden abrir en una aplicación del teléfono. La lupa y el botón Atrás están siempre visibles. `versionCode 18`, con la misma firma permanente.

## FocoQuiz v0.6.13 — Inicio al primer toque, protección y exámenes nuevos

En el bloqueo de aplicaciones, ambos botones «Ir al inicio» utilizan una ruta común: solicitan a Android abrir Inicio antes de desmontar el panel. Si Android no confirma el cambio de ventana, hacen **un único reintento automático**; no debe ser necesario tocar dos veces. La transición evita que reaparezca el bloqueo mientras se abre el launcher.

Cada vez que sales de un quiz para Inicio, otra app o una pantalla no relacionada, se descarta el intento actual (pregunta, puntuación y respuestas temporales). El siguiente intento vuelve a la pregunta 1 y se vuelve a seleccionar/mezclar el orden de las preguntas aleatoriamente, sin duplicados dentro del mismo intento. Consultar **Guía** o **Calculadora** durante el quiz no cuenta como abandono; el visor de guías devuelve a la pregunta que estabas respondiendo.

El servicio de Accesibilidad se reconecta/reanuda las comprobaciones cuando Android lo permite, incluso sin tener el dashboard abierto. Se añade en el dashboard «Ajustes de batería · mantener protección activa», que abre la pantalla correspondiente de Android para que el usuario elija «Sin restricciones» en su Samsung. Android puede detener el servicio tras forzar cierre, revocar Accesibilidad o por restricciones del fabricante: la app no puede garantizar ni imponer permanencia indefinida. La navegación del sistema, emergencias y permisos se mantienen bajo control del usuario.

El APK release continúa con la firma permanente y aumenta `versionCode` a 19 para actualizar sobre la v0.6.12 sin borrar los datos.

## FocoQuiz v0.6.14 — calculadora científica durante los exámenes

El botón pequeño **▦ Calculadora científica** se despliega dentro del cuestionario, tanto en el bloqueo por Accesibilidad como en los exámenes de planes de estudio. Conserva el progreso y no abre una ventana flotante. Añade **sin, cos, tan, asin, acos, atan, log base 10, ln, π, e, factorial, potencias (x², x³, xʸ), raíz cuadrada, inverso (1/x), porcentajes, paréntesis y notación científica EE**, además de las cuatro operaciones básicas. **DEG/RAD** cambia el modo angular; por defecto comienza en grados. Las funciones usan paréntesis (ejemplo: `sin(30)`, `2^3`, `log(100)`, `1.2E-3`). El porcentaje equivale a dividir por 100. Incluye protección contra divisiones por cero, errores de dominio y factoriales fuera de rango.

En respuestas escritas puedes pulsar **Usar resultado en mi respuesta**; en selección múltiple puedes consultar el resultado sin alterar las opciones. Funciona completamente sin Internet. El historial temporal de la calculadora no se guarda al salir del quiz. **Actualización firmada** con versión 0.6.14 y `versionCode 20`.

## FocoQuiz v0.6.15 — números diferentes en cada pregunta de cálculo

Las preguntas de **cálculo matemático, físico, electrónico y financiero** pueden incluir un bloque opcional `numeric_variation` en el JSON del examen. El prompt descargable del banco de preguntas ya solicita a la IA preparar las variables a partir de la guía (rangos, intervalos y fórmula) en lugar de guardar únicamente un número fijo. Al empezar **cada nuevo intento**, FocoQuiz sortea nuevos valores, sustituye las variables en el enunciado, calcula la respuesta con su motor científico local y crea opciones de selección múltiple nuevas con la respuesta correcta mezclada. La explicación también usa los datos actuales, y la calificación acepta formatos equivalentes como 2.5 y 2,50 para un mismo número. El cálculo es totalmente **offline**.

Ejemplo: `"question": "Con {V} voltios y {R} ohmios, ¿cuál es la corriente?"`, con `numeric_variation.variables` para V y R y `numeric_variation.answer_expression: "{V}/{R}"`. Este patrón permite crear cientos de variantes sin generar cientos de preguntas. Las preguntas teóricas, las estadísticas de aprendizaje y el orden aleatorio de preguntas se mantienen. El banco de fórmulas y la biblioteca enlazada siguen disponibles durante el quiz.

**Compatibilidad:** los exámenes existentes sin `numeric_variation` continúan funcionando, pero conservarán sus números originales. Para que las preguntas de cálculo de esos exámenes cambien, hay que regenerar su JSON con el nuevo prompt y volver a importarlo. Las operaciones matemáticas que vienen incluidas como demostración se convierten a preguntas parametrizadas.

Se mantiene la APK release con firma permanente y sube a versión 0.6.15, `versionCode 21`.

## FocoQuiz v0.6.16 — banco persistente de preguntas respondidas y números nuevos

Cada quiz utiliza un **banco de preguntas ya respondidas** que se conserva entre sesiones. Se guarda una marca al comprobar una respuesta, aunque sea incorrecta; simplemente abrir una pregunta o abandonar el examen sin contestarla no la consume. El siguiente intento prioriza preguntas que aún no se han respondido en ese conjunto de guías/dificultad. Si el cuestionario requiere más preguntas que las pendientes, utiliza todas las pendientes primero y completa con preguntas de un nuevo ciclo, sin repetir una pregunta dentro del mismo intento. El contador *Banco de respondidas: n / total* aparece en la pantalla de preguntas y en la de planes de estudio. El banco se vacía automáticamente al llegar a todas las preguntas elegibles y comienza un ciclo nuevo. Para evitar interferencias entre distintas combinaciones de guías/dificultad, cada conjunto tiene su propio banco.

**Números variables mejorados:** se recuerda la última variante de cada ejercicio y se evita repetir inmediatamente los mismos números cuando haya alternativas. También se reconocen preguntas guardadas anteriormente del tipo «¿Cuánto es 7 × 8?» y se convierten automáticamente a ejercicios parametrizados **solo cuando la operación y su respuesta original se verifican matemáticamente**. Otros problemas científicos, financieros, electrónicos o de texto requieren el campo `numeric_variation` del prompt actualizado; de lo contrario, sus cifras no se modifican automáticamente para evitar dar soluciones erróneas.

La versión se firma con el certificado privado estable de FocoQuiz, `versionCode 22`, y puede instalarse sobre v0.6.15 sin desinstalar.

## FocoQuiz v0.6.18 — banco global de preguntas respondidas

La versión v0.6.17 guardaba las preguntas respondidas en bancos separados según el conjunto exacto de guías y la dificultad de cada app. Por ello, una pregunta respondida podía reaparecer en un plan de estudio o en otra app con un conjunto parcialmente distinto. La v0.6.18 **unifica el historial por ID de pregunta** a través de los cuestionarios de desbloqueo y los planes de estudio: no se seleccionarán preguntas ya respondidas mientras existan suficientes preguntas sin responder. Cuando ya no queden suficientes pendientes para llenar el cuestionario, se podrán utilizar preguntas de un ciclo anterior, siempre **sin duplicar una pregunta dentro del mismo intento**. El banco global se vacía automáticamente al responder todas las preguntas disponibles.

El registro ocurre solo al pulsar Comprobar sobre una respuesta no vacía, independientemente de si es correcta o incorrecta. Salir con una pregunta pendiente **no** la marca como respondida. Se migran los bancos creados por versiones previas para conservar el avance. Las preguntas numéricas sin ID explícito reciben un ID estable derivado de su plantilla antes de sustituir valores, para que el cambio de números no impida reconocer una pregunta como respondida. El orden y los datos matemáticos se siguen mezclando por intento.

Los problemas antiguos sin configuración `numeric_variation` continúan mostrando números fijos salvo aritmética simple verificable; las instrucciones de importación actuales permiten generar plantillas variables. La APK release mantiene la firma permanente y sube a v0.6.18 / versionCode 24.
