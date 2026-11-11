# Notas Científicas v0.2
Aplicación Android Flutter independiente que combina notas editables, importación de PDF/TXT/MD/NCNOTE, escritura libre con S Pen y calculadora científica con historial.

El código fuente completo está guardado en `source.tar.xz`, un archivo TAR+XZ. El workflow de GitHub Actions lo extrae en esta carpeta y genera el APK de prueba. Esto evita afectar el código de Memora y FocoQuiz en este repositorio.

## Compilación
Abrir Actions > **Notas Cientificas - compilar APK** > descargar el artefacto **Notas-Cientificas-v0.2-debug-apk** si la compilación finaliza correctamente.

**Estado:** prototipo experimental de v0.2. No es una reproducción completa de Samsung Notes ni ha sido validada con S Pen en un dispositivo físico.


## Firma permanente y actualizaciones Android (desde v0.2.3)

La versión v0.2.3 y posteriores se compilan con una **clave PKCS12 fija**. La clave privada NO se almacena en este repositorio público. Es requisito un secreto de GitHub Actions:

- Nombre exacto: `NC_SIGNING_BUNDLE_B64`.
- Valor: todo el contenido (una sola línea) del archivo privado `SECRETO_COPIAR_EN_GITHUB.txt` entregado al propietario junto con `notas-cientificas-release.p12`.
- Configuración: `Settings > Secrets and variables > Actions > New repository secret` del repositorio `angeljo0801/ESTUDIO`.

El workflow de `.github/workflows/notas-cientificas-apk.yml` usa el secreto dentro del runner efímero, verifica el certificado y firma el APK release sin publicar la clave. Si falta el secreto, falla en lugar de producir un APK con la firma de depuración. El `versionCode` se incrementa automáticamente usando el número de ejecución del workflow.

**Paquete Android fijo:** `com.alascargo.notas_cientificas`.
**SHA-256 del certificado público permanente:** `3B:57:21:B7:6B:CE:B2:00:54:DD:2F:83:F1:74:B9:22:D1:D1:77:43:A8:5B:99:DA:AC:A7:9D:16:8D:86:9F:4A`.

**Migración:** Las compilaciones v0.2.1 y v0.2.2 tenían firmas de depuración diferentes. Sin las claves privadas antiguas, Android exigirá una **desinstalación inicial** para cambiar a la identidad permanente. Exporta o respalda las notas antes de desinstalar. Después de instalar la primera versión firmada con la clave permanente, las siguientes versiones podrán instalarse encima sin borrar los datos, siempre que mantengan el mismo `applicationId`, la misma clave y un `versionCode` superior.

**Backup crítico:** Guarda el archivo PKCS12 y el bundle de secretos en un almacenamiento privado y seguro. Perderlos impide seguir actualizando la aplicación bajo la misma firma.
