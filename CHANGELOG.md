# Changelog

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
