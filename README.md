# skills

Reusable AI-agent skills (SKILL.md format) and supporting template files, designed for Devin and compatible agents.

## Skills

| Skill | Description |
|-------|-------------|
| [create-from-template](.agents/skills/create-from-template/SKILL.md) | Create a final file from an existing template. Detects placeholders (any syntax), asks for all values at once with context-based suggestions, writes the filled output to a chosen path — template left untouched. |

Skills live under `.agents/skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`) followed by the workflow instructions.

## Supporting files

- `from-template/` — sample template files used to exercise the create-from-template skill (e.g. `template1.md`) and example outputs.
- `AGENTS.md` — working conventions for agents operating in this repo.
- `AGENTS.local.md` — personal working-style rules.

## Usage

Point your agent at this repo (or copy a skill folder into your project's `.agents/skills/` or `.devin/skills/`). When a request matches a skill's description — e.g. "create X from the template Y" — the agent loads the SKILL.md and follows its workflow.

## License

[MIT](LICENSE)
