---
name: ai724
description: Use when the user asks to read or change data on ai724.de (their job-application tracker) - jobs, applications, status, comments, CVs, cover letters, profile, templates, AI actions. Covers authentication (Firebase refresh token), the helper script, endpoints, and safety rules.
---

# ai724.de skill

ai724.de is the user's own job-application web app (FastAPI backend at `https://ai724.de/api`, Firebase auth, Bearer token). The credentials belong to a **test account** (`adelramezani.jd@gmail.com`).

## How to call it

Always use the helper `tools/ai724.py` inside this skill's folder (`<skill-dir>`; the folder is self-contained and works from any project). It refreshes the Firebase ID token itself (about 1h lifetime), retries dropped connections, and uses `curl` because Python's own HTTP gets a 407 from the corporate proxy.

```bash
export MSYS_NO_PATHCONV=1      # REQUIRED in Git Bash, else "/version" becomes a Windows path
cd <skill-dir>/tools
python ai724.py GET /version
python ai724.py GET /menu_list/ "profile_email=adelramezani.jd@gmail.com&offset=0&limit=100&search="
python ai724.py POST /jobs/ '{"link":"...","description":"...","title":"...","company":"...","source":"..."}'
```

From Python: `import os, sys; sys.path.insert(0, "<skill-dir>/tools"); import ai724; ai724.call(method, path, body=None, query="")`.
**`call` argument order is `(method, path, body, query)`**: for GET pass the query string as the 4th argument, not the 3rd.

Credentials (the helper takes the first it finds):
1. environment variables `AI724_API_KEY` and `AI724_REFRESH_TOKEN`, or
2. the file `<skill-dir>/.secrets/ai724.env` (`KEY=VALUE` lines with those names).

The helper needs only Python 3 (stdlib). It uses `curl` when present and falls back to urllib; set `AI724_NO_CURL=1` to force urllib. Never print, commit, copy or paste the credential values, and never put them in job records or project files. If the skill is installed inside a repo, its own `.gitignore` already excludes `.secrets/` and the token cache. If refresh fails (HTTP 400/401 from securetoken), the refresh token was revoked: ask the user for a new one (browser DevTools > Application > IndexedDB > `firebaseLocalStorageDb` > `firebaseLocalStorage` > `stsTokenManager.refreshToken`, and `apiKey` from the same record) and have them set it via env var or the env file, not in the chat.

## Install in another project

Copy this whole folder to `<project>/.claude/skills/ai724/` (or `~/.claude/skills/ai724/` for all projects on that machine). Then give it credentials via env vars or the `.secrets/ai724.env` file.

The live API spec is `https://ai724.de/api/openapi.json` (Swagger at `/api/docs`). Re-fetch it with curl if an endpoint behaves unexpectedly; the notes below can go stale.

## Data model (verified 2026-11-13)

- **Job**: `link, description, title, company, source` required; `detail` object optional; `job_id` assigned by the server.
- **Apply**: `job_id, profile_email, ai_gen_cv, ai_gen_cover, ai_gen_insight` required; `status` one of `ToDo, Applied, Interviewing, Offer, Rejected, NoResponse` (default `ToDo`); `detail` holds `history` (status changes and comments) and `questions` (AI Q&A).
- **Profile**: keyed by email; `GET /profiles/{email}` works. `GET /profiles/` (list) returns 500.

## Common operations

| Task | Call |
|---|---|
| Create job | `POST /jobs/` body Job |
| Create application | `POST /applies/` body Apply (CV/cover text from the project's own files; in the assistant repo these are `adel-ramezani/applications/<date>_<company>_<role>/`) |
| Read one | `GET /applies/{apply_id}`, `GET /jobs/{job_id}` |
| Change status | `PATCH /update_status/?apply_id=N&new_status=Applied` (query params, no body) |
| Add comment | `PATCH /add_comment/{apply_id}` body `{"text": "..."}` (appended to `detail.history`) |
| Replace AI CV / cover | `PATCH /update_ai_gen_cv/{apply_id}`, `PATCH /update_ai_gen_cover/{apply_id}` |
| Download CV / cover | `GET /cv_download/{apply_id}`, `GET /cover_download/{apply_id}` |
| One user's list | `GET /menu_list/?profile_email=...&offset=0&limit=100&search=` |
| AI actions | `quick_apply`, `gen_cover_letter`, `create_job_by_url`, `ai_question*`, `regen_job_insights`: these spend AI quota and may write data; confirm with the user first |

Each comment and status change is stored in `detail.history`; comments cannot be assumed deletable, so keep them deliberate.

## Known quirks

- `GET /jobs/` and `GET /applies/` are **not filtered by user**: they return all users' records (including `adelramezani.ds@gmail.com`'s ~100 applications). Treat other profiles' data as out of scope: never modify it, and prefer `menu_list` for the user's own view. The user knows about this issue.
- The host is intermittently unreachable (HTTP 000); the helper retries 4 times. Retry later before concluding it is down.
- Responses can be large (CV/cover text); print only the fields you need.

## Rules

1. Reads are fine at any time. Before any **write**, state what will change (endpoint, record, values) unless the user just asked for that exact change.
2. Only touch records created for the current task; look at a target before overwriting or deleting. Do not call DELETE endpoints without explicit instruction.
3. Mark an application `Applied` only when the user says so or a submission is verified. In the assistant repo, the local job record under `adel-ramezani/jobs/` is the source of truth; keep it consistent and say when the site and the local record disagree.
4. Never invent CV claims, screening answers or salary information in what you upload.
5. Use `adelramezani.jd@gmail.com` as the contact email in CVs and letters.
6. After a write, read the record back and report the real result.
