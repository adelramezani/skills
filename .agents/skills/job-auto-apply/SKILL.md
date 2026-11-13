---
name: job-auto-apply
description: End-to-end job application pipeline for the user - search postings by lane CV, tailor CV + cover letter, export PDFs, extract and answer application-form questions from a reusable Q&A bank, then fill and submit the form via browser (only with explicit per-application user approval). Works in any workspace that follows the layout contract below.
argument-hint: "[<job record path or URL> | search]"
allowed-tools:
  - read
  - write
  - edit
  - grep
  - glob
  - exec
  - mcp__mcp-playwright__browser_navigate
  - mcp__mcp-playwright__browser_snapshot
  - mcp__mcp-playwright__browser_find
  - mcp__mcp-playwright__browser_click
  - mcp__mcp-playwright__browser_type
  - mcp__mcp-playwright__browser_fill_form
  - mcp__mcp-playwright__browser_select_option
  - mcp__mcp-playwright__browser_press_key
  - mcp__mcp-playwright__browser_file_upload
  - mcp__mcp-playwright__browser_evaluate
  - mcp__mcp-playwright__browser_take_screenshot
  - mcp__mcp-playwright__browser_wait_for
  - mcp__mcp-playwright__browser_pdf_save
  - mcp__mcp-playwright__browser_handle_dialog
  - mcp__mcp-playwright__browser_close
---

# Job auto-apply pipeline

You are the user's job-application assistant. This skill holds the **procedure**; everything personal (name, locations, salary floor, lanes, CV files, contact email) comes from the user's workspace files, never from this skill and never from memory.

## Workspace contract

The **workspace root** is the folder holding the user's job-search `AGENTS.md` (ask the user once if you can't find it). Paths below are relative to it.

| File / folder | Purpose | If missing |
|---|---|---|
| `AGENTS.md` | Source of truth for preferences and hard filters: lanes and which CV file serves each, master CV, target locations and work authorization, employment type, minimum compensation and how to assess it, contact email, approval rules | Stop and ask the user to supply them; do not assume defaults |
| master CV + one CV file per lane (named in `AGENTS.md`) | Only source of claims you may use | Stop |
| `PLAYBOOK-job-search.md` (optional) | Daily-search procedure and job-record format | Use the record format below |
| `state/seen-jobs.md` | Dedup ledger, append-only, one line per vacancy | Create with a header |
| `state/last-run.md`, `state/boards.md` | Search watermark; boards to fetch (ATS endpoints) | Create when first needed |
| `state/screening-qa.md` | Reusable Q&A bank for application forms | Create |
| `jobs/<lane>/<date>_<company>_<role>.md` | One record per non-excluded vacancy | Create |
| `applications/<date>_<company>_<role>/` | `cv.md`, `cover-letter.md`, `screening-answers.md`, PDFs, `submission-confirmation.png` | Create |

Job record sections: Tracking (lanes, source URL/ID, dates, status, CV used) · Job description · Match assessment · Compensation (status, basis, range, source, date) · Application materials · Approval & submission · Activity log.

## Non-negotiable gates (never bypass; stricter project rules in `AGENTS.md` win)

- Submit ONLY after the user explicitly approves that specific application AND its final materials. One approval never covers another role. (If `AGENTS.md` records a documented, dated decision for fully automatic submission, follow its stated limits exactly.)
- Never invent CV claims, screening answers, dates, salary figures, or confirmation details. Use only evidence in the lane CVs / master CV.
- Mark `applied` only after verified submission confirmation (screenshot or confirmation text).
- Never store credentials, tokens, or identity documents in job records or the Q&A bank.
- Respect the minimum-compensation rule from `AGENTS.md`: statuses `potential`/`unknown` must be resolved with the user before submission; never submit `below` roles.
- Never solve captchas or create accounts without asking the user.

## Stage 0 - Resolve the target

- If the argument is a path to a job record or a source URL, open/match that record. If none exists, create it first.
- If the argument is `search` (or empty and the user asked to find jobs), run Stage 1.
- The record's `Status` says where to resume: `shortlist` -> Stage 2; `materials drafted` -> Stage 4/5 review; `approved` -> Stage 5 only.

## Stage 1 - Search (`search` mode only)

Follow `PLAYBOOK-job-search.md` if present, else:
1. Read `state/last-run.md` (watermark), `state/boards.md` (fetch ONLY listed boards), `state/seen-jobs.md` (dedup ledger).
2. Fetch/filter with a script. Never read raw board JSON into context; write pre-filtered candidates to a temp file. For LinkedIn, use the companion `linkedin-jobs` skill if installed (read-only search that returns candidates JSON; record IDs as `linkedin:<id>` in the ledger).
3. Classify each candidate into a lane by responsibilities (not title), apply the hard filters from `AGENTS.md` (location, language requirements vs the CV, employment type, compensation), compare requirements against the lane CV.
4. Write one record per non-excluded vacancy, append-only update `state/seen-jobs.md` (count lines before/after), update `state/boards.md` and `state/last-run.md`; commit/push only if the project's rules say to.
5. Present the shortlist and STOP for user selection.

## Stage 2 - Tailor CV + cover letter

Create `applications/<YYYY-MM-DD>_<company>_<role>/` (match existing folder naming).

**`cv.md`** - start from the lane CV named in the record's `CV used:` line (primary lane first):
- Keep the file's structure and section order. Re-emphasize and reorder existing evidence for the JD; adapt headline and summary.
- You may drop or shorten bullets, but NEVER add skills, titles, metrics or experience not present in the lane CV or master CV. Mirror the JD's vocabulary only where honest evidence exists.
- Keep location, work authorization and contact details exactly as the master CV states them.

**`cover-letter.md`** - start from the cover-letter template at the bottom of the lane CV, or the most recent `applications/*/cover-letter.md`:
- Specific to company + role; reference real projects and JD requirements; first person, factual, ~4-6 short paragraphs; fill bracketed placeholders with role-specific content.

Use the most recent existing application folders as format examples. Update the record's `Application materials` and activity log.

## Stage 3 - Export PDFs

Produce `<Full_Name>_CV_<Company>.pdf` and `<Full_Name>_Cover_Letter_<Company>.pdf` in the application folder (full name as in the master CV, underscores for spaces). Use the first available toolchain:
1. `pandoc cv.md -o <file>.pdf`
2. `weasyprint` / `wkhtmltopdf` on rendered HTML
3. Browser fallback: render the markdown to clean HTML (serif/sans ~11pt, A4 margins), open the `file://` URL in the browser tool, save as PDF.

Verify the PDF exists and is non-trivial in size before continuing.

## Stage 4 - Extract form questions, answer from the Q&A bank

1. **Get the real field list** from the actual application form, never from the JD text:
   - Ashby: POST `https://jobs.ashbyhq.com/api/non-user-graphql` (`ApiJobPosting` op); if that fails, open `https://jobs.ashbyhq.com/<org>/<jobId>` in the browser and snapshot the form.
   - Greenhouse: `https://boards-api.greenhouse.io/v1/boards/<slug>/jobs/<id>?questions=true`.
   - Personio: `application_form_fields_v2` in the job page JSON; also snapshot the rendered form (it can contain required custom fields the API omits).
   - Anything else: open it in the browser and snapshot the form DOM.
2. **Answer each field** from `state/screening-qa.md` and the lane CV. Reuse stored canonical answers verbatim for repeat questions (name, email, phone, location, work authorization, sponsorship, notice period, salary expectation, profile links, relocation, AI-processing consent, referral source, start date).
3. **Ask the user** (one batched question) only for questions with no stored answer or that are role-specific ("Why this company?", essays - draft from CV evidence and mark as draft).
4. **Write `screening-answers.md`**: table `| Question | Required | Draft answer | Source |` plus free-text sections.
5. **Append newly answered questions** to `state/screening-qa.md` (normalized question -> canonical answer -> source -> date). Never store home address or ID documents there.

## Stage 5 - Approval -> fill -> submit

1. **STOP.** Present cv.md, cover-letter.md, screening-answers.md and the salary status. Get explicit approval for THIS application. Consent and recruiter-contact questions may also need the user.
2. Fill the form in the browser: navigate to the apply URL, snapshot, fill text fields, select dropdowns, upload the PDFs (trigger the file chooser first if needed), paste approved essay text.
3. Final review snapshot, then submit - the click on Submit/Apply needs the user's confirmed go-ahead in this session.
4. Verify confirmation (success text or email), save a screenshot as `submission-confirmation.png` in the application folder.
5. Update the record (`Approval & submission`, status `applied`, activity log) and append `applied` to the ledger line for the source ID. If the outcome is uncertain, record `submission uncertain` and check for confirmation before any retry, to avoid duplicates.

## Environment notes

- Browser automation: the `allowed-tools` above use the `mcp-playwright` MCP server. On a platform without it, use that platform's equivalent browser tool, or `scripts` driven by Playwright; the gates do not change.
- Prefer shell/python scripts for bulk fetching and filtering; keep raw data out of the model's context.
