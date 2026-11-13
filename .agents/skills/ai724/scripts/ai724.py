"""Small client for the ai724.de API (Firebase-authenticated). Part of the `ai724` skill.

Credentials come from an env file with two lines (never commit it):
    AI724_API_KEY=...
    AI724_REFRESH_TOKEN=...
Lookup order: $AI724_ENV_FILE, ./.secrets/ai724.env (current directory), ~/.ai724/ai724.env.
The short-lived ID token is cached next to the env file as ai724.idtoken.json.

CLI:
    python ai724.py GET /version
    python ai724.py GET /menu_list/ "profile_email=<email>&offset=0&limit=100&search="
    python ai724.py POST /jobs/ '{"link": "...", "description": "...", "title": "...", "company": "...", "source": "..."}'
Library:
    sys.path.insert(0, "<skill>/scripts"); from ai724 import call; call("GET", "/version")
    call(method, path, body=None, query="")   # for GET pass the query string as the 4th argument
"""
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.parse

BASE = os.environ.get("AI724_BASE_URL", "https://ai724.de/api")


def env_path() -> pathlib.Path:
    candidates = [os.environ.get("AI724_ENV_FILE"),
                  pathlib.Path.cwd() / ".secrets" / "ai724.env",
                  pathlib.Path.home() / ".ai724" / "ai724.env"]
    for c in candidates:
        if c and pathlib.Path(c).is_file():
            return pathlib.Path(c)
    raise FileNotFoundError(
        "ai724 credentials not found. Set AI724_ENV_FILE or create ./.secrets/ai724.env "
        "or ~/.ai724/ai724.env with AI724_API_KEY and AI724_REFRESH_TOKEN.")


def _curl(method, url, headers=None, data=None, form=None, retries=4):
    """HTTP via curl (honours system proxy settings); returns (status, text). Retries on connection failure."""
    cmd = ["curl", "-sS", "-m", "60", "-X", method, "-w", "\n%{http_code}", url]
    for k, v in (headers or {}).items():
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


def _env(path=None):
    d = {}
    for line in (path or env_path()).read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def id_token():
    """Return a valid Firebase ID token, refreshing it when <5 min remain."""
    env_file = env_path()
    cache = env_file.with_name("ai724.idtoken.json")
    try:
        c = json.loads(cache.read_text())
        if c["exp"] - time.time() > 300:
            return c["token"]
    except Exception:
        pass
    e = _env(env_file)
    form = urllib.parse.urlencode({"grant_type": "refresh_token", "refresh_token": e["AI724_REFRESH_TOKEN"]})
    code, text = _curl("POST", "https://securetoken.googleapis.com/v1/token?key=" + e["AI724_API_KEY"], form=form)
    if code != 200:
        raise RuntimeError(f"token refresh failed: HTTP {code}")
    r = json.loads(text)
    tok = r["id_token"]
    cache.write_text(json.dumps({"token": tok, "exp": time.time() + int(r["expires_in"])}))
    if r.get("refresh_token") and r["refresh_token"] != e["AI724_REFRESH_TOKEN"]:
        env_file.write_text(env_file.read_text().replace(e["AI724_REFRESH_TOKEN"], r["refresh_token"]))
    return tok


def call(method, path, body=None, query=""):
    url = BASE + path + ("?" + query if query else "")
    headers = {"Authorization": "Bearer " + id_token(), "Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body)
    code, text = _curl(method, url, headers=headers, data=data)
    if code >= 400:
        raise RuntimeError(f"HTTP {code}: {text[:500]}")
    return json.loads(text) if text.strip() else None


if __name__ == "__main__":
    m, p = sys.argv[1], sys.argv[2]
    q = sys.argv[3] if len(sys.argv) > 3 and m == "GET" else ""
    b = json.loads(sys.argv[3]) if len(sys.argv) > 3 and m != "GET" else None
    print(json.dumps(call(m, p, b, q), indent=2, ensure_ascii=False))
