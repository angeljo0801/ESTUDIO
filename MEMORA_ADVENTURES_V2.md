# Memora Aventuras – contenido remoto v2

El APK contiene el reproductor; Memora-Sync privado contiene historias y arte. No se ejecuta código remoto.

## Guías y progreso
Conservar ID de guía, ID de tarjeta y número de capítulo. Incrementar revisión de guía para cambios de contenido. Conservar campaign.version y orden de jornadas para no reiniciar partidas de comercio. Para aventuras genéricas, los capítulos explícitos se numeran desde 1 sin huecos y se agregan al final. Una tarjeta de escena puede tener chapter para agrupar desafíos. Las tarjetas de una guía que no se incluyen en una revisión se conservan.

## Arte
En cada fila de memora-guides.json, añadir "art":{"revision":1,"parts":["r1_part_01","r1_part_02"]}. Publicar primero cada archivo adventure-art/<id-guia>/<id-parte>.json, luego el catálogo. Cada parte es menor de 900000 bytes. Formato:
```json
{"schema":2,"kind":"memora_adventure_art_v2","adventure":"marketing-futuro","assets":{"future_city":"BASE64_WEBP","mentor":"BASE64_WEBP","mentor_happy":"BASE64_WEBP"}}
```
IDs de recursos en ASCII minúscula, números y guion bajo. Las partes conforman el paquete completo; no deltas. Incrementar revision gráfica incluso si el texto no cambia. Usar rutas nuevas por revisión. Máximo 64 partes, 512 recursos, 32 MiB por aventura. Cada recurso máximo 1.2M caracteres base64; el límite remoto por parte sigue siendo 900000 bytes. Instalación local atómica y funcionamiento offline. El paquete v1 de Nébula se conserva.

## Escenas
Agregar a cualquier memora_scene_v1 o jornada de memora_trade_campaign_v1:
```json
{"visual":{"background":"future_city","height":320,"actors":[{"id":"mentor","expression":"happy","label":"Mentor","position":-0.85,"scale":1.1},{"id":"hero","label":"Tú","position":0.85,"scale":1}]}}
```
La expresión busca id_expression y vuelve a id. Recomendado WebP transparente para actores. Máximo 4 por escena, posiciones -1 a 1, altura 200–420. Reparto opcional: tarjeta con kind memora_cast_v2, characters [{id,name,role,bio}]. Diálogos y preguntas siguen el formato existente. Los desafíos y simulaciones usan mecánicas existentes; nuevas mecánicas ejecutables requieren actualizar APK.

## Uso
Biblioteca → Memora-Sync → Sincronizar guías, personajes y paisajes. Hay actualización exclusiva del arte e importación manual por aventura.

## Música ambiental (reproductor v1.55)
Cada escena o jornada admite el campo opcional `"music":"mystery"`. Valores: `adventure`, `study`, `mystery`, `battle`, `victory`, `silent`. Si falta, el reproductor elige según el bioma, rol y fase. Los cambios de contenido se sincronizan sin reinstalar. Las cinco pistas originales se sintetizan localmente y no necesitan internet; el selector de música guarda el nivel de volumen. No se admiten archivos de audio nuevos en esta revisión.
