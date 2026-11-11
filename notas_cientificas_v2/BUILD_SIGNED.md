# Compilación de Notas Científicas v0.2.3

Compilación solicitada tras configurar el secreto de firma de Android en GitHub Actions.

El workflow debe comprobar el certificado de firma permanente y compilar un APK release con package id com.alascargo.notas_cientificas. Si la clave falta o no coincide, la tarea debe detenerse sin publicar ningún APK.

El secreto está configurado en GitHub Actions, no debe guardarse aquí.
