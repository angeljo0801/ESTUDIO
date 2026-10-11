# FocoQuiz: firma permanente de APK (configuración una sola vez)

Para que una actualización conserve las aplicaciones y sus datos, debe utilizar el mismo identificador (com.focoquiz.app), el mismo certificado de firma y un versionCode mayor.

## Seguridad

- ESTUDIO es un repositorio PUBLICO. **Nunca subas el archivo .p12, el Base64 de la clave o la contraseña a un commit, issue o conversación.**
- Guarda dos copias seguras del paquete privado con la clave. Si se pierde, no se podrán firmar futuras actualizaciones compatibles.
- La clave solo se descifra temporalmente en GitHub Actions y NO se publica junto con la APK.
- Las APK debug anteriores usaban certificados distintos. Como no necesitas conservar sus datos, desinstalarás la versión vieja UNA SOLA VEZ para instalar la primera versión de firma estable.

## PASO 1: Crea dos secretos en GitHub

En https://github.com/angeljo0801/ESTUDIO entra a:
Settings > Secrets and variables > Actions > Repository secrets > New repository secret

- Nombre: FOCOQUIZ_SIGNING_BUNDLE_B64
  Valor: pega el contenido COMPLETO, en una sola línea, del archivo FOCOQUIZ_SIGNING_BUNDLE_B64.txt del paquete privado.
- Nombre: FOCOQUIZ_SIGNING_PASSWORD
  Valor: pega la contraseña de FOCOQUIZ_SIGNING_PASSWORD.txt sin incluir el salto de línea final.

Ambos archivos proceden del mismo paquete. No generes una clave nueva para cada APK.

## PASO 2: Compila la primera APK estable

1. Ve a https://github.com/angeljo0801/ESTUDIO/actions/workflows/focoquiz-stable-apk.yml
2. Selecciona Run workflow en la rama main.
3. Espera al resultado SUCCESS.
4. Abre el trabajo terminado, sección Artifacts, y descarga FocoQuiz-v0.6.5-APK-FIRMA-ESTABLE.
5. Extrae el ZIP. El archivo instalable se llama app-release.apk.
6. Desinstala la versión anterior de FocoQuiz (una única vez), acepta que perderás los datos actuales, e instala esta APK de firma estable.
7. Vuelve a habilitar manualmente los permisos del teléfono, si los necesitas.

## PASO 3: Actualizaciones futuras

En cada versión posterior:
- Incrementar versionCode en la aplicación.
- Seguir usando esos DOS secretos, sin cambiar la clave.
- Ejecutar FocoQuiz · APK estable actualizable.
- Abrir el nuevo app-release.apk SOBRE la anterior (sin desinstalar).

Android aceptará la actualización si la clave sigue igual, el ID no cambia y versionCode aumenta.

Importante: una firma estable no da Accesibilidad automática y no elimina las restricciones de seguridad de Android para servicios sensibles.

Primera versión prevista para firma estable: v0.6.5 (versionCode 11).
