#!/usr/bin/env python3
"""Enable signing for FocoQuiz release builds using a permanent private PKCS#12 key.

Never check the keystore or password into GitHub; this patch only reads
environment variables populated from encrypted GitHub Actions secrets.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
build = root / "app/build.gradle.kts"
content = build.read_text(encoding="utf-8")
needle = '''    compileOptions {
'''
signature = '''    // Release keystore supplied only at build time from encrypted GitHub secrets.
    signingConfigs {
        create("focoquizPermanent") {
            storeFile = file(System.getenv("FOCOQUIZ_SIGNING_FILE")
                ?: error("Falta FOCOQUIZ_SIGNING_FILE"))
            storeType = "PKCS12"
            storePassword = System.getenv("FOCOQUIZ_SIGNING_PASSWORD")
                ?: error("Falta FOCOQUIZ_SIGNING_PASSWORD")
            keyAlias = "focoquiz"
            keyPassword = System.getenv("FOCOQUIZ_SIGNING_PASSWORD")
                ?: error("Falta FOCOQUIZ_SIGNING_PASSWORD")
        }
    }
    buildTypes {
        getByName("release") {
            signingConfig = signingConfigs.getByName("focoquizPermanent")
            isMinifyEnabled = false
        }
    }

'''
if 'create("focoquizPermanent")' in content:
    print("Firma estable ya configurada.")
else:
    if needle not in content:
        raise SystemExit("No se encontro el bloque compileOptions del build Gradle")
    content = content.replace(needle, signature + needle, 1)
    build.write_text(content, encoding="utf-8")
    print("FocoQuiz release signing enabled (key provided via environment).")
