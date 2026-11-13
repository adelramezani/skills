# job-auto-apply — portable AI agent skill

A job-application procedure for AI agents: search, shortlist, tailor CV and cover letter, export PDFs, answer form questions from a reusable Q&A bank, then fill and submit the form **only after your explicit approval of each application**. It contains no personal data: your name, lanes, CVs, locations, salary floor and contact email come from your workspace files.

Single file: `SKILL.md` (this README is just for humans).

## Install

| Platform | Copy the `job-auto-apply/` folder to |
|---|---|
| Claude Code (all projects) | `~/.claude/skills/job-auto-apply/` (Windows: `%USERPROFILE%\.claude\skills\job-auto-apply\`) |
| Claude Code (one project) | `<project>/.claude/skills/job-auto-apply/` |
| Agents using the Agent Skills layout | `<project>/.agents/skills/job-auto-apply/` or that agent's documented skills folder |
| Agents without skill support | any folder in the repo, plus one line in its instruction file: `For job applications follow <path>/job-auto-apply/SKILL.md.` |

Restart the agent afterwards. Folder locations vary by agent and version; check its docs if the skill isn't picked up.

## What the new project must provide (the "workspace contract")

1. An **`AGENTS.md`** with your job-search preferences: lanes and the CV file for each, master CV, target locations and work authorization, employment type, minimum compensation and how to assess it, contact email, and your approval rules.
2. A **master CV and one CV file per lane**. The skill only ever uses claims found there.
3. Optional: `PLAYBOOK-job-search.md`, `state/` files (`seen-jobs.md`, `last-run.md`, `boards.md`, `screening-qa.md`), `jobs/`, `applications/`. The skill creates the ones it needs.

If `AGENTS.md` or the CVs are missing, the skill stops and asks you. It does not guess defaults.

## Tooling

- The `allowed-tools` list in `SKILL.md` names the `mcp-playwright` MCP server (browser navigation, form filling, uploads, screenshots, PDF save). Install that MCP server, or edit the list to your agent's browser tools. Without a browser tool, the skill still does everything up to Stage 4 (materials and answers).
- PDF export needs `pandoc` or `weasyprint`, or falls back to the browser's PDF save.
- Optional companion skills: `linkedin-jobs` (read-only LinkedIn search) and `ai724` (ai724.de tracker).

## Safety gates (built in)

Per-application approval before any submit; no invented claims or answers; `applied` only after verified confirmation; no credentials in records; compensation rules from `AGENTS.md` enforced; no captcha solving or account creation without asking. If your `AGENTS.md` records a deliberate, dated decision for fully automatic submission, the skill follows that decision's limits instead.
