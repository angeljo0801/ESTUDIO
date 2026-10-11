#!/usr/bin/env python3
"""FocoQuiz v0.6.6: optional permanent signing from protected GitHub Actions secrets."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'app/build.gradle.kts'
s=path.read_text(encoding='utf-8')
if 'versionName = "0.6.5"' not in s or 'versionCode = 11' not in s:
    raise SystemExit('Expected FocoQuiz v0.6.5 base')
anchor='''    defaultConfig {
'''
if anchor not in s: raise SystemExit('Gradle android defaultConfig anchor missing')
s=s.replace(anchor,'''    // For private, reusable APK signing only.
    // GitHub stores the PKCS12 keystore and password in encrypted Actions secrets.
    // Ordinary PR builds use a temporary debug certificate, not a release artifact.
    signingConfigs {
        getByName("debug") {
            val stableKeystore = System.getenv("FOCOQUIZ_KEYSTORE_FILE")
            val stablePassword = System.getenv("FOCOQUIZ_KEYSTORE_PASSWORD")
            if (!stableKeystore.isNullOrBlank() && !stablePassword.isNullOrBlank()) {
                storeFile = file(stableKeystore)
                storeType = "pkcs12"
                storePassword = stablePassword
                keyAlias = "focoquiz_stable"
                keyPassword = stablePassword
            }
        }
    }
''' + '''    // A real release APK is not debuggable. Sign it only when the secret key is available.
    buildTypes {
        getByName("release") {
            if (!System.getenv("FOCOQUIZ_KEYSTORE_FILE").isNullOrBlank()) {
                signingConfig = signingConfigs.getByName("debug")
            }
            isMinifyEnabled = false
        }
    }
''' + anchor,1)
s=s.replace('versionName = "0.6.5"','versionName = "0.6.6"').replace('versionCode = 11','versionCode = 12')
path.write_text(s,encoding='utf-8')
print('FocoQuiz v0.6.6 signing configured: only encrypted GitHub secrets unlock reusable key.')
