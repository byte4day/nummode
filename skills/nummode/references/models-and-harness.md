# Models and harness (Nov 2026)

Use this when authoring or updating skills/agents, or when a brief asks which model to pin. Prefer **host defaults** and `inherit` unless a specialist tradeoff is clear. Do not invent model IDs.

## Recommended pins (when you must pin)

| Host / provider | Prefer | Also useful | Avoid as defaults |
|---|---|---|---|
| Claude Code / Anthropic | `inherit`, or alias `opus` / `sonnet` / `haiku` / `fable` | Full IDs `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-2` | Hard-coding retired generations (e.g. Sonnet 4.5) |
| Codex / OpenAI | host default; Astra for hardest work | `gpt-6-astra`, `gpt-6.1-sol`, `gpt-6.1-terra`, `gpt-6-luna` (availability is plan-dependent) | Assuming every ChatGPT plan has Sol/Astra |
| Cursor | `model: inherit` on custom agents | Host picker / Composer when the user chooses it | Pinning vendor IDs Cursor does not list |
| Gemini / Antigravity / OpenCode | that CLI's current default | Pass `--model` via `relay.py` only when the worker CLI documents it | Guessing undocumented IDs |

Sources: [Claude models overview](https://platform.claude.com/docs/en/models/overview), [Claude Code sub-agents](https://code.claude.com/docs/en/sub-agents), [Using GPT-6](https://developers.openai.com/api/docs/guides/latest-model/gpt-6-astra.md), [Cursor skills](https://cursor.com/docs/skills).

## Skill packaging (Agent Skills)

Skills follow the open [Agent Skills](https://agentskills.io/) format: a folder with `SKILL.md` (`name` + `description`), optional `scripts/`, `references/`, `assets/`. Hosts load name/description first, then the body on activation (progressive disclosure).

| Host | User skills | Project skills | Docs |
|---|---|---|---|
| Claude Code | `~/.claude/skills/<name>/` | `.claude/skills/<name>/` | [code.claude.com/docs/en/skills](https://code.claude.com/docs/en/skills) |
| Codex | `~/.agents/skills/<name>/` | `.agents/skills/` (cwd → repo root) | [learn.chatgpt.com/docs/build-skills](https://learn.chatgpt.com/docs/build-skills) |
| Cursor | `~/.agents/skills/`, `~/.cursor/skills/` | `.agents/skills/`, `.cursor/skills/` | [cursor.com/docs/skills](https://cursor.com/docs/skills) |
| Antigravity / Gemini | `~/.gemini/config/skills/` (legacy antigravity paths still scanned) | `.agents/skills/` | host docs |
| OpenCode | follow that CLI's skill roots | project `.agents/skills/` when supported | host docs |

Optional Codex/ChatGPT UI metadata: `agents/openai.yaml` inside the skill.

## Authoring rules for current models

1. **Short descriptions.** Front-load the trigger. Bad: "use for anything involving databases". Good: "use when adding or changing a migration".
2. **Router-shaped SKILL.md.** Keep the root thin; push detail into `references/` loaded only when needed.
3. **Native workers first.** Same-host Task / Agent / subagents beat cross-CLI `relay.py`. Relay is for a different vendor, a second opinion, or true background isolation.
4. **Less recipe, more contract.** Stronger models (Fable, Opus 5.5, GPT-6 Astra) need clear goals, constraints, and verification — not every micro-step.
5. **AGENTS.md / rules:** point at docs by situation; do not require reading the whole tree before every edit.

See also: [Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).
