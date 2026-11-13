---
name: ai724
description: Use when the user asks to read or change data on ai724.de (a job-application tracker they have an account on) - jobs, applications, status, comments, CVs, cover letters, profile, templates, AI actions. Covers authentication (Firebase refresh token), the bundled helper script, endpoints, and safety rules.
---

# ai724.de skill

ai724.de is a job-application web app (FastAPI backend at `https://ai724.de/api`, Firebase auth, Bearer token). The user's own account email, contact email and where local job records live are **project settings**: take them from the project's instructions (`AGENTS.md` / `CLAUDE.md`), never guess them.

## How to call it

Use the bundled helper `scripts/ai724.py` (next to this file). It refreshes the Firebase ID token itself (about 1h lifetime), retries dropped connections, and shells out to `curl` so system proxy settings apply. Needs Python 3 and `curl`.

```bash
export MSYS_NO_PATHCONV=1      # REQUIRED in Git Bash on Windows, else "/version" becomes a Windows path
python <skill>/scripts/ai724.py GET /version
python <skill>/scripts/ai724.py GET /menu_list/ "profile_email=<user-email>&offset=0&limit=100&search="
python <skill>/scripts/ai724.py POST /jobs/ '{"link":"...","description":"...","title":"...","company":"...","source":"..."}'
```

From Python: `import sys; sys.path.insert(0, "<skill>/scripts"); import ai724; ai724.call(method, path, body=None, query="")`.
**`call` argument order is `(method, path, body, query)`**: for GET pass the query string as the 4th argument, not the 3rd.

## Credentials

An env file with `AI724_API_KEY` and `AI724_REFRESH_TOKEN`, found via: `$AI724_ENV_FILE`, then `./.secrets/ai724.env`, then `~/.ai724/ai724.env`. A cached `ai724.idtoken.json` is written next to it. Keep that folder out of git. Never print, commit, copy or paste these values, and never put them in job records. If a project stores the file elsewhere, its instructions should say which `AI724_ENV_FILE` to use.

If refresh fails (HTTP 400/401 from securetoken), the refresh token was revoked: ask the user for a new one (browser DevTools > Application > IndexedDB > `firebaseLocalStorageDb` > `firebaseLocalStorage` > `stsTokenManager.refreshToken`, and `apiKey` from the same record) and have them put it in the env file, not the chat.

The live API spec is `https://ai724.de/api/openapi.json` (Swagger at `/api/docs`). Re-fetch it with curl if an endpoint behaves unexpectedly; the notes below can go stale.

## Data model (verified 2026-11-13)

- **Job**: `link, description, title, company, source` required; `detail` object optional; `job_id` assigned by the server.
- **Apply**: `job_id, profile_email, ai_gen_cv, ai_gen_cover, ai_gen_insight` required; `status` one of `ToDo, Applied, Interviewing, Offer, Rejected, NoResponse` (default `ToDo`); `detail` holds `history` (status changes and comments) and `questions` (AI Q&A).
- **Profile**: keyed by email; `GET /profiles/{email}` works. `GET /profiles/` (list) returned 500.

## Common operations

| Task | Call |
|---|---|
| Create job | `POST /jobs/` body Job |
| Create application | `POST /applies/` body Apply (use the CV/cover files from the project's application folder) |
| Read one | `GET /applies/{apply_id}`, `GET /jobs/{job_id}` |
| Change status | `PATCH /update_status/?apply_id=N&new_status=Applied` (query params, no body) |
| Add comment | `PATCH /add_comment/{apply_id}` body `{"text": "..."}` (appended to `detail.history`) |
| Replace AI CV / cover | `PATCH /update_ai_gen_cv/{apply_id}`, `PATCH /update_ai_gen_cover/{apply_id}` |
| Download CV / cover | `GET /cv_download/{apply_id}`, `GET /cover_download/{apply_id}` |
| One user's list | `GET /menu_list/?profile_email=...&offset=0&limit=100&search=` |
| AI actions | `quick_apply`, `gen_cover_letter`, `create_job_by_url`, `ai_question*`, `regen_job_insights`: these spend AI quota and may write data; confirm with the user first |

Each comment and status change is stored in `detail.history`; comments cannot be assumed deletable, so keep them deliberate.

## Known quirks

- `GET /jobs/` and `GET /applies/` are **not filtered by user**: they return all users' records. Treat other profiles' data as out of scope: never modify it, and prefer `menu_list` for the user's own view.
- The host is intermittently unreachable (HTTP 000); the helper retries 4 times. Retry later before concluding it is down.
- Responses can be large (CV/cover text); print only the fields you need.

## Rules

1. Reads are fine at any time. Before any **write**, state what will change (endpoint, record, values) unless the user just asked for that exact change.
2. Only touch records created for the current task; look at a target before overwriting or deleting. Do not call DELETE endpoints without explicit instruction.
3. Mark an application `Applied` only when the user says so or a submission is verified. If the project keeps local job records, they are the source of truth: keep them consistent and say when the site and the local record disagree.
4. Never invent CV claims, screening answers or salary information in what you upload.
5. Use the contact email from the project instructions in CVs and letters.
6. After a write, read the record back and report the real result.
