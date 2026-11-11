"""Configure stable Android release signing for Notas Cientificas.

The permanent private key is NOT stored in this public GitHub repository.
A single Actions secret, NC_SIGNING_BUNDLE_B64, contains the encoded PKCS12 keystore
and its password. This is invoked only inside the ephemeral GitHub Actions runner.
"""
from pathlib import Path
import base64
import hashlib
import json
import os
import re
import subprocess

BASE = Path("notas_cientificas_v2")
BUNDLE_ENV = "NC_SIGNING_BUNDLE_B64"
EXPECTED_CERT_SHA256 = "3b5721b76bceb20054dd2f83f174b922d1d17743a85b99daaca79d168d869f4a"

raw = os.environ.get(BUNDLE_ENV, "").strip()
if not raw:
    raise SystemExit(
        "Falta el secreto NC_SIGNING_BUNDLE_B64. En el repositorio ESTUDIO, "
        "abre Settings > Secrets and variables > Actions > New repository secret, "
        "pega el contenido completo de SECRETO_COPIAR_EN_GITHUB.txt "
        "y vuelve a ejecutar GitHub Actions."
    )

try:
    bundle = json.loads(base64.b64decode(raw, validate=True).decode("utf-8"))
    alias = bundle["alias"]
    password = bundle["password"]
    key_bytes = base64.b64decode(bundle["keystore"], validate=True)
except Exception as exc:
    raise SystemExit("El secreto NC_SIGNING_BUNDLE_B64 no tiene el formato correcto.") from exc

if not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", alias):
    raise SystemExit("Alias de firma invalido.")
if not re.fullmatch(r"[a-zA-Z0-9_-]{16,150}", password):
    raise SystemExit("Contrasena de firma invalida.")
if not 1000 < len(key_bytes) < 131072:
    raise SystemExit("El keystore no tiene un tamaño esperado.")

key_path = BASE / "android/app/notas-cientificas-release.p12"
key_path.write_bytes(key_bytes)
key_path.chmod(0o600)
try:
    cert = subprocess.run(
        [
            "keytool", "-exportcert", "-alias", alias,
            "-keystore", str(key_path), "-storetype", "PKCS12",
            "-storepass", password,
        ],
        capture_output=True, check=True,
    ).stdout
except subprocess.CalledProcessError as exc:
    raise SystemExit("No se pudo validar la firma permanente.") from exc

actual_fingerprint = hashlib.sha256(cert).hexdigest()
if actual_fingerprint != EXPECTED_CERT_SHA256:
    raise SystemExit(
        "La clave proporcionada no coincide con la identidad de firma permanente "
        "de Notas Cientificas. No se compilara un APK incompatible."
    )

props = BASE / "android/key.properties"
props.write_text(
    "storeFile=app/notas-cientificas-release.p12\n"
    f"storePassword={password}\n"
    f"keyPassword={password}\n"
    f"keyAlias={alias}\n",
    encoding="utf-8",
)
props.chmod(0o600)

gradle = BASE / "android/app/build.gradle.kts"
s = gradle.read_text(encoding="utf-8")
if 'signingConfigs.getByName("debug")' not in s:
    raise SystemExit("No se encuentra la configuracion de firma predeterminada de Flutter.")
if 'val notasSigningProperties' not in s:
    s = "import java.util.Properties\nimport java.io.FileInputStream\n\n" + s
    marker = "android {"
    inject = '''val notasSigningProperties = Properties()
val notasSigningFile = rootProject.file("key.properties")
check(notasSigningFile.exists()) { "No hay configuracion de firma release" }
FileInputStream(notasSigningFile).use { notasSigningProperties.load(it) }

android {'''
    if marker not in s:
        raise SystemExit("No se encontro el bloque android de Gradle.")
    s = s.replace(marker, inject, 1)
    marker = "    buildTypes {"
    release = '''    signingConfigs {
        create("notasRelease") {
            keyAlias = notasSigningProperties.getProperty("keyAlias")
            keyPassword = notasSigningProperties.getProperty("keyPassword")
            storeFile = rootProject.file(notasSigningProperties.getProperty("storeFile"))
            storePassword = notasSigningProperties.getProperty("storePassword")
        }
    }
    buildTypes {'''
    if marker not in s:
        raise SystemExit("No se encontro el bloque buildTypes de Gradle.")
    s = s.replace(marker, release, 1)
s = s.replace(
    'signingConfig = signingConfigs.getByName("debug")',
    'signingConfig = signingConfigs.getByName("notasRelease")',
    1,
)
gradle.write_text(s, encoding="utf-8")

pubspec = BASE / "pubspec.yaml"
v = pubspec.read_text(encoding="utf-8")
if "version: 0.2.2+4" not in v:
    raise SystemExit("La version de origen es diferente de la esperada.")
pubspec.write_text(
    v.replace("version: 0.2.2+4", "version: 0.2.3+5", 1),
    encoding="utf-8",
)
print("Firma release permanente configurada y certificado verificado.")
