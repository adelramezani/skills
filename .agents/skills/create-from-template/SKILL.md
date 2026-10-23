---
name: create-from-template
description: Create a final file from an existing template file. Use when the user asks to "create X from the template Y" — reads the named template, auto-detects placeholders, asks the user for all placeholder values at once (suggesting values from context), then writes the filled-in result to a user-chosen output path while leaving the template untouched.
---

# create-from-template

Produce a final, filled-in file from an existing template file.

## Trigger

Any request of the form "create X from the template Y" — the user names a template file and wants a completed copy of it.

## Workflow

1. Locate and read the template file the user named.
2. Scan the template and auto-detect placeholders. Placeholders may appear in any syntax — e.g. `[FULL NAME]`, `{{name}}`, `<NAME>`, `TODO(...)` — treat anything that clearly marks a spot to be filled as a placeholder.
3. Ask the user for all placeholder values **at once** (one question/message listing every placeholder). For each placeholder, suggest a value inferred from context where possible (e.g. current date, repo name, existing files, earlier conversation). Never silently invent values — the user confirms or overrides every suggestion.
4. If the user has not already defined an output path, ask where to write the output file.
5. Write the filled-in file to the chosen path. The template file must remain byte-for-byte unchanged.

## Rules

- Never modify the template file.
- Always ask the user for placeholder values — do not guess and fill without confirmation.
- If a placeholder-looking string is ambiguous (it might be intended to stay literal, e.g. inside an example or code block), include it in the question and let the user decide.
- Output is a single file.

## Done

The output file exists at the chosen path and is not empty.

## Example

User: "Create my job-search assistant prompt from the template from-template/template1.md"

1. Read `from-template/template1.md`.
2. Detect placeholders: `[FULL NAME]`, `[USER-DIR as FULL NAME lower case and replace spaces with hyphens]` (appears in the heading and body).
3. Ask the user, with suggestions:
   - `FULL NAME` — suggested: `Adel Ramezani` (inferred from the repo name `adelramezani/assistant` referenced in the template).
   - `USER-DIR` — suggested: `adel-ramezani` (derived per the placeholder's own rule).
   - Output path — suggested: `job-search-assistant.md`.
4. Write the result, e.g. line 1 becomes `Daily job-search assistant for Adel Ramezani` and `[USER-DIR]` occurrences become `adel-ramezani/`.
5. Template file left untouched.
