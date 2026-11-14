# Changelog

## 2.3.0 — 2026-11-14

### Added
- **Streams**: a brief with two or more deliverables ("update A, also build B, one more thing: C") gets a `streams:` block from `route.py`, one line per deliverable with its own mission and skills. Each stream's process skill (design, author, research, debug) joins the main plan. `--no-streams` turns it off.
- **claude.ai skills are indexed**: the newest `~/.claude/skills/synced/<account>/` folder is indexed as `anthropic-skills:<name>`, so `anthropic-skills:skill-creator`, `pdf`, `docx` and the rest can fill slots.
- **Claude Code built-in skills** (`code-review`, `simplify`, `security-review`, `run`, `update-config`, `plugin-authoring`, `claude-api`) are added to the pool when the harness is Claude Code.
- **Relay fan-out**: `relay.py dispatch --to codex,claude --task "…"` sends the same task to each harness for independent answers.
- **`relay.py clean`** removes finished task folders (`--older-than DAYS`, `--all`, `--dry-run`). Running tasks are never touched.
- **Failure reasons**: `relay.py wait` and `status` print a `why:` line for failed and timed-out tasks, taken from the task log.
- `research` mission: `deep-research` is the first candidate and the slot is required; new signals (deep research, sources, cite, fact-check, literature, state of the art); optional `agent-reach` slot.
- `design-ui` signals: animation, animated, svg, 3d.

### Fixed
- A brief that names an installed skill and asks to change it ("update my copycat skill and add features") now routes to the `skill` mission. It used to land on `build` because of "add" and "create".
- Skill names written with a space match: "copy cat" finds `copycat`.
- Filler verbs in skill descriptions (create, update, feature, text, add, fix…) no longer count as keyword hits. They pulled in unrelated skills on long briefs.
- A secondary mission's required slot no longer reports a gap. Only the primary mission's required slots do.
- `route.py --file <missing>` printed a Python traceback. It now exits 2 with a one-line error.
- `relay.py status`, `wait`, `result`, `cancel` and `clean` created an empty `.relay/` folder in whatever directory they ran in. Only `dispatch` creates it now.
- `relay.py cancel` on a finished task overwrote its status with `cancelled`. A finished task now keeps its outcome.
- A worker that ignored SIGTERM at timeout hung the runner forever. It is killed after 5 seconds.
- `relay.py dispatch` with a missing `--task-file`, an empty task, `--timeout 0` or a missing `--cwd` printed a traceback or started a task that could not run. Each is now a one-line error with exit 2.
- `relay.py wait` with no tasks said nothing. It now says so.
- Gemini CLI sessions are detected as the `gemini` harness.

### Tests
- 72 unit tests (was 52): indexer 20, relay 20, router 32. Installer smoke test unchanged at 11 checks.

## 2.2.1 — 2026-11-10

### Fixed
- **Cursor harness filter** now includes `claude` and `codex` skill roots. Cursor loads those directories for compatibility ([docs](https://cursor.com/docs/skills)), so routing inside a Cursor session no longer drops skills that only live under `~/.claude/skills`.
- CLI router tests clear leaked `CURSOR_AGENT` / Claude / Codex env vars and assert the Cursor path still finds Claude-installed skills.

## 2.2.0 — 2026-11-10

### Added
- **`references/models-and-harness.md`**: current Claude / OpenAI / Cursor model guidance (Nov 2026), Agent Skills packaging paths, and short-description authoring rules.
- Skill-authoring defaults in `SKILL.md` for mission `skill` (Agent Skills shape, progressive disclosure, prefer native Task/Agent over same-host relay).

### Changed
- Shortened the skill `description` so hosts that truncate skill catalogs keep the trigger words.
- Relay guidance: prefer same-host Agent/Task; pin `--model` only to IDs the worker CLI documents.
- Agent blurbs mention Claude alias `fable` and current GPT-6 / Claude 5.5 lines without hard-requiring them.
- Installer keeps one canonical skill at `~/.agents/skills/nummode`, links only into `~/.claude/skills`, and removes duplicate Cursor/Codex skill symlinks (those hosts already read `~/.agents/skills`).
- Installer also ships optional Codex UI metadata at `agents/openai.yaml`.

## 2.1.0 — 2026-10-22

### Added
- **Relay (`relay.py`)**: the orchestrating agent can launch Claude Code, Codex, Cursor, Antigravity (via Gemini CLI) and OpenCode headless, give each a sub-task, and continue from the saved `.relay/<id>/result.md`. Commands: `harnesses`, `dispatch`, `status`, `wait`, `result`, `cancel`. Modes `read` (default) / `write` / `full` map to each CLI's own sandbox and approval flags. Background by default, `--wait` for foreground. Recursion guard (workers cannot start workers), timeouts, `.gitignore` in the relay root. Standard library only.
- **`relay` mission** in the router, with signals such as "with codex", "delegate to", "hand off".
- Tests: `tests/test_relay.py` (11, fake harness binaries).

### Changed
- Saying "use nummode to …" no longer forces the `skill` mission; only "update/improve/fix nummode" does.

## 2.0.0 — 2026-10-11

### Added
- **`route.py` router**: turns a brief into a ranked skill plan (`nummode · <mission> · skills: …`), with reasons, gaps and an "also considered" list. Supports `--json`, `--mission`, `--harness`, `--file`/stdin, `--repo` stack detection and `--limit`. Refreshes the index automatically when skills change.
- **Slot-based playbooks**: each mission is a table of slots (`required` / `optional` / `match`) with ordered fallback candidates and globs. The router parses `missions.md` directly, so the model and the script share one source of truth.
- **New missions**: `refactor` and `skill` (author or improve skills, agents, hooks, CLAUDE.md).
- **Claude Code plugin skills** (e.g. `vercel:deploy`, `stripe:stripe-docs`) are indexed from enabled plugins.
- **Harness awareness**: every skill records `found_in`. The router filters to skills the current harness can load (auto-detected).
- `refresh-index.py --check` (exit 3 when stale), `--quiet`, `NUMMODE_HOME`, `NUMMODE_EXTRA_ROOTS`.
- **Size gate**: small asks run in lite mode without ceremony.
- Stuck rule (3 failed attempts → change approach), explicit rules for irreversible actions, and a fixed report shape.
- Tests: indexer (18), router + cross-file mission contract (23), installer smoke test in a temp `$HOME` (11 checks). CI runs them on Python 3.11 and 3.13 plus shellcheck, with SHA-pinned actions and read-only permissions.
- `uninstall.sh --purge`.

### Changed
- Skill count is now **1–7**, sized to the brief (was a fixed 3–7, which contradicted the one-skill `logo` mission).
- Tagging uses skill names first and needs 2 or more description hits, which ends false tags like `vercel-composition-patterns → deploy`.
- Signals match whole words, so "checkout" no longer triggers `audit`.
- Agent files for Claude, Cursor and Codex share one contract text.

### Fixed
- The installer put `nummode.bak.*` backups inside skill roots, where harnesses loaded them as a duplicate `nummode` skill. Backups now go to `~/.nummode/backups/`, and old ones are moved there on install.
- The index was built before harness links existed, so it was stale right after install.
- The indexer skips hidden, backup and `__pycache__` dirs.
- `uninstall.sh` kept deleting user playbooks and backups. It now removes only shipped files, and harness links only when they are symlinks.

## 1.1.0
- Antigravity/Gemini roots, collision warnings, atomic index writes, install footgun fixes.
