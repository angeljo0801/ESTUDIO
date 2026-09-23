from pathlib import Path
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: patch_file_bridge_auth_v2.py <file_bridge.dart> <FileBridgeService.kt>")

dart_path = Path(sys.argv[1])
service_path = Path(sys.argv[2])

# Client: send the token in both Authorization and a bridge-specific header.
s = dart_path.read_text()
old = "req.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');"
new = "req.headers.set(HttpHeaders.authorizationHeader, 'Bearer $token');\n        req.headers.set('X-Local-Manager-Token', token);"
if old not in s and "X-Local-Manager-Token', token" not in s:
    raise RuntimeError("Dart health auth anchor not found")
if old in s:
    s = s.replace(old, new, 1)

old = "req.headers.set(HttpHeaders.authorizationHeader, 'Bearer ${widget.token}');"
new = "req.headers.set(HttpHeaders.authorizationHeader, 'Bearer ${widget.token}');\n        req.headers.set('X-Local-Manager-Token', widget.token);"
if old in s:
    s = s.replace(old, new)
elif "X-Local-Manager-Token', widget.token" not in s:
    raise RuntimeError("Dart browser auth anchor not found")

dart_path.write_text(s)

# Host: persist the selected token synchronously and accept either auth header.
s = service_path.read_text()
old = """            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putInt(KEY_PORT, port)
                .putString(KEY_TOKEN, token)
                .apply()""
new = """            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit()
                .putInt(KEY_PORT, port)
                .putString(KEY_TOKEN, token)
                .commit()""
if old in s:
    s = s.replace(old, new, 1)
elif ".putString(KEY_TOKEN, token)\n                .commit()" not in s:
    raise RuntimeError("Native token persistence anchor not found")

old = """            val expected = activeToken
            val auth = headers["authorization"].orEmpty()
            if (expected.length < 16 || auth != "Bearer $expected") {
                sendText(output, 401, "Unauthorized")
                return
            }""
new = """            val expected = activeToken
            val bridgeToken = headers["x-local-manager-token"].orEmpty()
            val auth = headers["authorization"].orEmpty()
            val authenticated = expected.length >= 16 && (
                bridgeToken == expected || auth == "Bearer $expected"
            )
            if (!authenticated) {
                sendText(
                    output,
                    401,
                    if (bridgeToken.isEmpty() && auth.isEmpty()) {
                        "Unauthorized: token header missing"
                    } else {
                        "Unauthorized: token mismatch"
                    }
                )
                return
            }""
if old in s:
    s = s.replace(old, new, 1)
elif 'headers["x-local-manager-token"]' not in s:
    raise RuntimeError("Native auth validation anchor not found")

service_path.write_text(s)
print("Local Manager bridge authentication v2 patch applied")
