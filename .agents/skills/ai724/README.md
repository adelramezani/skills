# ai724 — portable AI agent skill

Lets an AI agent read and update your jobs and applications on **ai724.de** through its API. Self-contained: `SKILL.md` (instructions), `scripts/ai724.py` (client), `scripts/test_ai724.py`.

## Install

| Platform | Copy the `ai724/` folder to |
|---|---|
| Claude Code (all projects) | `~/.claude/skills/ai724/` (Windows: `%USERPROFILE%\.claude\skills\ai724\`) |
| Claude Code (one project) | `<project>/.claude/skills/ai724/` |
| Agents using the Agent Skills layout | `<project>/.agents/skills/ai724/` or that agent's documented skills folder |
| Agents without skill support | any folder in the repo, plus one line in its instruction file (`AGENTS.md`, `.cursor/rules`, `GEMINI.md`, ...): `For ai724.de tasks follow <path>/ai724/SKILL.md.` |

Skill-folder locations vary by agent and version; check your agent's docs if the skill isn't picked up. Restart the agent afterwards.

## Requirements

Python 3 and `curl` on the PATH. No pip packages (tests need `pytest`).

## Credentials

Create an env file (outside git) containing:

```
AI724_API_KEY=<firebase web api key>
AI724_REFRESH_TOKEN=<firebase refresh token>
```

The script looks for it at `$AI724_ENV_FILE`, then `./.secrets/ai724.env`, then `~/.ai724/ai724.env`. Get the values from your signed-in ai724.de browser session (DevTools > Application > IndexedDB > `firebaseLocalStorageDb` > `firebaseLocalStorage`: `apiKey` and `stsTokenManager.refreshToken`). Never paste them into an agent chat; put them in the file yourself. The script rotates the refresh token in the file when Firebase issues a new one and caches the short-lived token next to it.

## Project settings (put these in the project's AGENTS.md, not in the skill)

Your ai724 account email, your CV contact email, where local job records and application folders live, and `AI724_ENV_FILE` if you keep the env file somewhere non-standard.

## Verify

```bash
export MSYS_NO_PATHCONV=1                              # Git Bash on Windows only
python -m pytest <path>/ai724/scripts -q               # offline tests
python <path>/ai724/scripts/ai724.py GET /version      # live check
```

Notes: `AI724_BASE_URL` overrides the API base. `GET /jobs/` and `GET /applies/` return all users' records (a known server quirk), so the skill tells the agent to stay within your own records.
