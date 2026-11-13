"""Small client for the ai724.de API (Firebase-authenticated). Portable: stdlib only.

Credentials, first match wins:
  1. environment variables  AI724_API_KEY, AI724_REFRESH_TOKEN
  2. file <skill dir>/.secrets/ai724.env  (KEY=VALUE lines, same names)

Transport: uses `curl` when available (works through authenticated corporate
proxies where urllib gets 407), otherwise falls back to urllib.

Usage:
    python ai724.py GET /menu_list/ "profile_email=...&offset=0&limit=100&search="
    python ai724.py POST /jobs/ '{"...": "..."}'
    (Git Bash on Windows: export MSYS_NO_PATHCONV=1 so "/version" is not rewritten)
Library:
    from ai724 import call; call("GET", "/version")        # call(method, path, body, query)
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("AI724_BASE", "https://ai724.de/api")
SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
ENV = SKILL_DIR / ".secrets" / "ai724.env"
_cache_dir = ENV.parent if ENV.parent.is_dir() else pathlib.Path(tempfile.gettempdir())
CACHE = _cache_dir / "ai724.idtoken.json"


def _http(method, url, headers=None, data=None, form=None, retries=4):
    """Return (status, text). Retries on connection failure."""
    headers = dict(headers or {})
    if shutil.which("curl") and not os.environ.get("AI724_NO_CURL"):
        cmd = ["curl", "-sS", "-m", "60", "-X", method, "-w", "\n%{http_code}", url]
        for k, v in headers.items():
            cmd += ["-H", f"{k}: {v}"]
        if form:
            cmd += ["--data", form]
        if data is not None:
            cmd += ["--data-binary", "@-"]
        last = ""
        for _ in range(retries):
            p = subprocess.run(cmd, input=data, capture_output=True, text=True, encoding="utf-8")
            if p.returncode == 0:
                body, _, code = p.stdout.rpartition("\n")
                return int(code), body
            last = p.stderr.strip()
            time.sleep(3)
        raise ConnectionError(last)
    payload = form.encode() if form else (data.encode("utf-8") if data is not None else None)
    if form:
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    last = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, payload, headers, method=method)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:  # connection problems
            last = e
            time.sleep(3)
    raise ConnectionError(str(last))


def _creds():
    key, rt = os.environ.get("AI724_API_KEY"), os.environ.get("AI724_REFRESH_TOKEN")
    if key and rt:
        return key, rt, False
    if not ENV.exists():
        raise SystemExit(
            "No credentials: set AI724_API_KEY and AI724_REFRESH_TOKEN, or create " + str(ENV)
        )
    d = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d["AI724_API_KEY"], d["AI724_REFRESH_TOKEN"], True


def id_token():
    """Return a valid Firebase ID token, refreshing it when <5 min remain."""
    try:
        c = json.loads(CACHE.read_text())
        if c["exp"] - time.time() > 300:
            return c["token"]
    except Exception:
        pass
    key, rt, from_file = _creds()
    form = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": rt})
    code, text = _http("POST", "https://securetoken.googleapis.com/v1/token?key=" + key, form=form)
    if code != 200:
        raise RuntimeError(f"token refresh failed: HTTP {code} (refresh token revoked or key wrong?)")
    r = json.loads(text)
    tok = r["id_token"]
    try:
        CACHE.write_text(json.dumps({"token": tok, "exp": time.time() + int(r["expires_in"])}))
    except OSError:
        pass
    new_rt = r.get("refresh_token")
    if from_file and new_rt and new_rt != rt:  # Google rotated it: keep the file current
        ENV.write_text(ENV.read_text(encoding="utf-8").replace(rt, new_rt), encoding="utf-8")
    return tok


def call(method, path, body=None, query=""):
    url = BASE + path + ("?" + query if query else "")
    headers = {"Authorization": "Bearer " + id_token(), "Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body)
    code, text = _http(method, url, headers=headers, data=data)
    if code >= 400:
        raise RuntimeError(f"HTTP {code}: {text[:500]}")
    return json.loads(text) if text.strip() else None


if __name__ == "__main__":
    m, p = sys.argv[1], sys.argv[2]
    q = sys.argv[3] if len(sys.argv) > 3 and m == "GET" else ""
    b = json.loads(sys.argv[3]) if len(sys.argv) > 3 and m != "GET" else None
    print(json.dumps(call(m, p, b, q), indent=2, ensure_ascii=False))
