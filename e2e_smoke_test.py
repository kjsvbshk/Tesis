"""
Prueba de humo end-to-end contra producción (Render).
Flujo: health -> modelo -> OTP -> registro -> login -> partidos -> prediccion -> apuesta -> creditos/historial.

Uso:
    python e2e_smoke_test.py
    (pedira el codigo OTP que llega a tu Gmail)

Solo usa la libreria estandar. No guarda credenciales: la cuenta es
desechable (usuario aleatorio, email con +tag hacia tu mismo inbox).
"""

import base64
import hashlib
import hmac
import json
import random
import string
import struct
import sys
import time
import urllib.request
import urllib.error


def totp(secret_b32: str, period: int = 30, digits: int = 6) -> str:
    """Codigo TOTP (RFC 6238) — mismo algoritmo que Google Authenticator/pyotp."""
    key = base64.b32decode(secret_b32.upper() + "=" * (-len(secret_b32) % 8))
    counter = struct.pack(">Q", int(time.time()) // period)
    mac = hmac.new(key, counter, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    code = (struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)

BASE = "https://tesis-waun.onrender.com"
API = BASE + "/api/v1"
EMAIL_BASE = "alisson.ingsoft"          # Gmail: los +tags llegan al mismo inbox
BET_AMOUNT = 50.0

TAG = "".join(random.choices(string.digits, k=4))
USERNAME = f"haw_e2e_{TAG}"
EMAIL = f"{EMAIL_BASE}+haw.e2e.{TAG}@gmail.com"
PASSWORD = "E2e!" + "".join(random.choices(string.ascii_letters + string.digits, k=12))

results = []


def req(method, url, body=None, token=None, timeout=45):
    """Devuelve (status_code, dict|str)."""
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw
    except Exception as e:
        return 0, str(e)


def step(n, name, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    icon = "✅" if ok else "❌"
    print(f"{icon} [{n:>2}] {mark:4} | {name}" + (f" | {detail}" if detail else ""))
    results.append((n, name, ok))
    return ok


def main():
    print("=" * 72)
    print(f"HAW E2E Smoke Test -> {BASE}")
    print(f"Cuenta de prueba: {USERNAME} / {EMAIL}")
    print(f"Password (desechable): {PASSWORD}")
    print("=" * 72)

    # 1. Health (con reintento por cold start de Render)
    code, body = req("GET", f"{BASE}/health", timeout=90)
    if code == 0:
        print("   (cold start? reintentando en 30s...)")
        time.sleep(30)
        code, body = req("GET", f"{BASE}/health", timeout=90)
    step(1, "GET /health", code == 200, f"HTTP {code} {body}")

    # 2. Modelo activo v3.1.0
    code, body = req("GET", f"{BASE}/debug/model", timeout=60)
    text = json.dumps(body) if isinstance(body, dict) else str(body)
    ok = code == 200 and "v3.1.0" in text
    step(2, "Modelo activo = v3.1.0", ok, f"HTTP {code} | {text[:160]}")

    # 3. Enviar OTP de registro (y verificar que NO viene en la respuesta)
    code, body = req("POST", f"{API}/users/send-verification-code",
                     {"email": EMAIL, "purpose": "registration"})
    sent = code == 200
    step(3, "POST send-verification-code", sent, f"HTTP {code} {body}")
    leak = isinstance(body, dict) and "code" in body
    step(4, "Seguridad: OTP NO viaja en la respuesta HTTP", sent and not leak,
         "sin campo 'code'" if not leak else "FUGA: el codigo aparece en el body")
    if not sent:
        finish(); return

    # 5. Registro con el OTP del inbox
    otp = input(f"\n>> Codigo de 6 digitos enviado a {EMAIL} (revisa Gmail): ").strip()
    code, body = req("POST", f"{API}/users/register",
                     {"username": USERNAME, "email": EMAIL,
                      "password": PASSWORD, "verification_code": otp})
    ok = code in (200, 201) and isinstance(body, dict)
    step(5, "POST /users/register", ok, f"HTTP {code} | rol={body.get('rol') if isinstance(body, dict) else body}")
    if not ok:
        finish(); return

    # 6. Login con password INCORRECTA -> 401 y mensaje generico
    code, body = req("POST", f"{API}/users/login",
                     {"username": USERNAME, "password": "Incorrecta123!"})
    detail = body.get("detail", "") if isinstance(body, dict) else str(body)
    step(6, "Login invalido devuelve 401 generico", code == 401 and "Traceback" not in detail,
         f"HTTP {code} | {detail[:60]}")

    # 7. Login correcto
    code, body = req("POST", f"{API}/users/login",
                     {"username": USERNAME, "password": PASSWORD})
    token = body.get("access_token") if isinstance(body, dict) else None
    step(7, "POST /users/login -> JWT", code == 200 and bool(token),
         f"HTTP {code} | rol={body.get('rol') if isinstance(body, dict) else '?'}")
    if not token:
        finish(); return

    # 8. Perfil: creditos iniciales
    code, body = req("GET", f"{API}/users/me", token=token)
    credits0 = float(body.get("credits") or 0) if isinstance(body, dict) else 0
    step(8, "GET /users/me (creditos iniciales)", code == 200 and credits0 > 0,
         f"HTTP {code} | credits={credits0}")

    # 9. Partidos proximos (fallback: today -> listado)
    match = None
    for path in ("/matches/upcoming", "/matches/today", "/matches/?limit=10"):
        code, body = req("GET", f"{API}{path}", token=token)
        if code == 200 and isinstance(body, list) and body:
            match = body[0]
            break
    step(9, "GET /matches (hay partidos)", match is not None,
         f"game_id={match.get('id')} {match.get('status')}" if match else f"HTTP {code}")
    if match is None:
        finish(); return

    # 10. Prediccion ML (intenta hasta 5 partidos; luego /predict/upcoming)
    pred, pred_game = None, None
    code, body = req("GET", f"{API}/matches/upcoming", token=token)
    candidates = body if (code == 200 and isinstance(body, list) and body) else [match]
    for m in candidates[:5]:
        gid = m.get("id")
        code, body = req("GET", f"{API}/predict/game/{gid}", token=token, timeout=90)
        if code == 200 and isinstance(body, dict):
            pred, pred_game = body, m
            break
    if pred is None:
        code, body = req("GET", f"{API}/predict/upcoming?days=3", token=token, timeout=120)
        if code == 200 and isinstance(body, list) and body:
            pred = body[0]
            pred_game = next((m for m in candidates if m.get("id") == pred.get("game_id")), match)
    p = float(pred.get("home_win_probability", -1)) if isinstance(pred, dict) else -1
    mv = pred.get("model_version") if isinstance(pred, dict) else None
    step(10, "Prediccion ML valida (0<p<1)", pred is not None and 0.0 < p < 1.0,
         f"P(home)={p:.4f} | modelo={mv} | latencia={pred.get('inference_latency_ms') if pred else '?'}ms"
         if pred else "sin prediccion disponible")

    # 11. Colocar apuesta moneyline al equipo local
    bet_game = pred_game or match
    gid = bet_game.get("id")
    team_id = bet_game.get("home_team_id") or bet_game.get("away_team_id")
    odds = float(bet_game.get("home_odds") or 1.85)
    payload = {"game_id": gid, "bet_type": "moneyline", "bet_amount": BET_AMOUNT,
               "odds": odds, "potential_payout": round(BET_AMOUNT * odds, 2),
               "selected_team_id": team_id}
    code, body = req("POST", f"{API}/bets/", payload, token=token)
    bet_ok = code in (200, 201) and isinstance(body, dict)
    bet_id = body.get("id") if bet_ok else None
    step(11, "POST /bets (moneyline 50 creditos)", bet_ok,
         f"HTTP {code} | bet_id={bet_id} odds={odds}" if bet_ok else f"HTTP {code} | {str(body)[:140]}")

    # 12. Debito de creditos verificado
    code, body = req("GET", f"{API}/users/me", token=token)
    credits1 = float(body.get("credits") or -1) if isinstance(body, dict) else -1
    expected = credits0 - BET_AMOUNT
    step(12, "Creditos debitados correctamente", bet_ok and abs(credits1 - expected) < 0.01,
         f"{credits0} -> {credits1} (esperado {expected})")

    # 13. Historial y resumen
    code, body = req("GET", f"{API}/bets/", token=token)
    in_hist = code == 200 and isinstance(body, list) and any(b.get("id") == bet_id for b in body)
    step(13, "Apuesta en historial (pending)", in_hist, f"HTTP {code} | {len(body) if isinstance(body, list) else 0} apuestas")
    code, body = req("GET", f"{API}/bets/stats/summary", token=token)
    step(14, "GET /bets/stats/summary", code == 200, f"HTTP {code} | {str(body)[:120]}")

    # ── 2FA (TOTP, como Google Authenticator — NO llega por correo) ────────
    # 15. Setup: el backend entrega el secreto (en la app real se escanea el QR)
    code, body = req("POST", f"{API}/users/me/2fa/setup", {}, token=token)
    secret = body.get("secret") if isinstance(body, dict) else None
    step(15, "POST /me/2fa/setup (secreto TOTP + backup codes)", code == 200 and bool(secret),
         f"HTTP {code} | backup_codes={len(body.get('backup_codes', [])) if isinstance(body, dict) else 0}")

    if secret:
        # 16. Activar 2FA con un codigo TOTP calculado del secreto
        code, body = req("POST", f"{API}/users/me/2fa/enable", {"code": totp(secret)}, token=token)
        step(16, "POST /me/2fa/enable (codigo TOTP valido)", code == 200,
             f"HTTP {code} | {str(body)[:80]}")

        # 17. Login SIN codigo 2FA -> debe rechazarse (401 + X-Requires-2FA)
        code, body = req("POST", f"{API}/users/login",
                         {"username": USERNAME, "password": PASSWORD})
        step(17, "Login sin codigo 2FA es rechazado", code == 401,
             f"HTTP {code} | {str(body.get('detail') if isinstance(body, dict) else body)[:70]}")

        # 18. Login CON codigo TOTP -> token
        code, body = req("POST", f"{API}/users/login",
                         {"username": USERNAME, "password": PASSWORD,
                          "two_factor_code": totp(secret)})
        token2 = body.get("access_token") if isinstance(body, dict) else None
        step(18, "Login con codigo TOTP entrega JWT", code == 200 and bool(token2),
             f"HTTP {code}")

    finish()


def finish():
    print("\n" + "=" * 72)
    passed = sum(1 for *_, ok in results if ok)
    print(f"RESULTADO: {passed}/{len(results)} pasos PASS")
    for n, name, ok in results:
        if not ok:
            print(f"  FALLO -> [{n}] {name}")
    print("=" * 72)
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
