<p><img src="assets/icon.svg" alt="nummode routing monogram" width="72" height="72"></p>

# nummode

**Paste a big prompt. nummode picks the skills, does the work, and proves it works.**

Runs on **Claude Code**, **Cursor** and **Codex**. Also indexes **Gemini / Antigravity** skill roots and enabled **Claude Code plugin** skills.

```text
you:      [1200-word product brief]
nummode · build · skills: writing-plans, supabase, frontend-design, verification-before-completion
          → plans → builds → runs the tests → reports what works and how to try it
```

---

## Why

Agent harnesses load dozens of skills. Nobody should have to pick which ones fire.

nummode is the routing layer:

1. **Size gate**: small asks skip the ceremony
2. **Intake**: goal, deliverables, constraints, stack, success test
3. **Route**: `route.py` detects the mission and ranks the installed skills
4. **Invoke**: load each skill right before its step
5. **Execute**: parallel only when streams share nothing
6. **Verify**: real commands before "done"
7. **Relay**: hand sub-tasks to other harnesses (Codex, Cursor, Claude Code, Antigravity, OpenCode) and read back their results
8. **Report**: what works, how to try it, one next action

The pasted brief is the approval. nummode never asks which skills to use.

---

## Install

```bash
git clone https://github.com/byte4day/nummode.git
cd nummode
./install.sh            # Claude + Cursor + Codex
./install.sh claude     # or one harness: claude | cursor | codex
```

| Flag | Effect |
|---|---|
| `--set-default` | Make nummode the Claude Code default agent even if another default is set |
| `--force-multi-agent` | Change Codex `multi_agent = false` to `true` |

Re-running is safe. Backups of anything replaced go to `~/.nummode/backups/`, never next to a skill root, so harnesses do not load a stale copy.

**Update:** `./update.sh` (`git pull --ff-only` + reinstall)

**Via the skills CLI:** `npx skills add byte4day/nummode -g -y` installs only the skill. Run `./install.sh` afterwards for the agents, playbooks and index. Without them the skill still works: it falls back to its bundled `references/` and `scripts/`.

### What gets installed

| Target | Path |
|---|---|
| Shared data | `~/.nummode/`: playbooks, `scripts/route.py`, `scripts/relay.py`, `scripts/refresh-index.py`, skill index, `VERSION`, `backups/` |
| Universal skill | `~/.agents/skills/nummode`, symlinked into each harness |
| Claude agent | `~/.claude/agents/nummode.md`. Sets the default `agent` only when none is set |
| Cursor agent | `~/.cursor/agents/nummode.md` |
| Codex role | `~/.codex/agents/nummode.toml`. Enables `features.multi_agent` when it is missing |

---

## Usage

| Harness | Start |
|---|---|
| Claude Code | `claude --agent nummode`, or any session once it is the default agent |
| Cursor | `@nummode` on a big prompt, or let the skill auto-trigger |
| Codex | Agent role `nummode`, or invoke the skill |

### The router

```bash
python3 ~/.nummode/scripts/route.py "build a stripe checkout in next.js with supabase auth and deploy it to vercel"
```

```text
nummode · build+deploy · skills: supabase, saas-auth-billing, vercel:auth, vercel:marketplace, vercel:deployments-cicd, project-delivery-checks

mission: build (signals: build) · secondary: deploy
  1. supabase                 [domain] score 11 · named in brief; kw: supabase, auth, next.js; tag
  2. saas-auth-billing        [domain] score  5 · kw: auth, checkout, stripe; tag
  3. vercel:auth              [domain] score  4 · kw: auth, next.js, vercel
  4. vercel:marketplace       [domain] score  4 · kw: build, checkout, vercel; tag
  5. vercel:deployments-cicd  [deploy] score  7 · kw: build, deploy, vercel; slot deploy +4
  6. project-delivery-checks  [verify] score  5 · tag; slot verify +4
harness: claude · index: fresh (66 skills, catalog=80ae5a1f090ad1f7)
```

| Option | Effect |
|---|---|
| `--file brief.md` / `-` | Read the brief from a file or stdin |
| `--mission audit` | Force a mission |
| `--harness claude\|cursor\|codex\|gemini\|any` | Only skills that harness can load. Auto-detected |
| `--repo PATH` | Read stack hints (package.json, pyproject, vercel.json…) from PATH. Default: cwd |
| `--json` | Machine-readable plan |
| `--limit N` | Cap the number of skills. Default 7 |

The router rebuilds the index automatically when skills change on disk. Manual: `python3 ~/.nummode/scripts/refresh-index.py` (`--check` exits 3 when stale).

### Relay: other harnesses as workers

<p><img src="assets/relay.svg" alt="nummode relay mark: one orchestrator routing to three workers" width="56" height="56"></p>

nummode can launch **Claude Code, Codex, Cursor, Antigravity (Gemini CLI) and OpenCode** headless, hand each one a sub-task, and continue from what they save. One harness orchestrates; the others are workers, like subagents across vendors.

```text
you:      use nummode: research rate-limiting options with Codex, then implement the best one
claude:   relay.py dispatch --to codex --task "Research … cite sources, recommend one"
codex:    works headless → .relay/<id>/result.md
claude:   relay.py wait → reads result.md → implements → runs the tests
```

```bash
R=~/.nummode/scripts/relay.py
python3 $R harnesses                                   # installed CLIs; marks the current session
python3 $R dispatch --to codex  --name research --task "…"           # background, read-only
python3 $R dispatch --to cursor --name ui-review --task "…" --context src/app.tsx
python3 $R wait                                        # block until all finish
python3 $R status                                      # done / failed / timeout / running
python3 $R result <id>                                 # print result.md
```

| Mode | Claude Code | Codex | Cursor | Gemini / Antigravity | OpenCode |
|---|---|---|---|---|---|
| `read` (default) | read/search tools only | `-s read-only` | `--mode ask` | `--approval-mode default` | no `--auto` |
| `write` | `acceptEdits` | `-s workspace-write` | `--force` | `auto_edit` | `--auto` |
| `full` | skip permissions | no sandbox | `--force` | `yolo` | `--auto` |

Each task folder holds `brief.md`, `prompt.txt`, `meta.json` (command, pids, status, exit code), `result.md`, `log.txt` and a `files/` dir. The relay root gets a `.gitignore` so handoffs never get committed. Workers cannot start workers (depth limit 1, `NUMMODE_RELAY_MAX_DEPTH`). Other options: `--mode`, `--model`, `--timeout`, `--cwd`, `--dir` / `NUMMODE_RELAY_DIR`, `--extra <raw-arg>`, `--wait`, `--dry-run`, `--json`. Override a binary with `NUMMODE_RELAY_<HARNESS>_BIN`.

[Copycat](https://github.com/byte4day/Copycat) and [DevOps Agent](https://github.com/byte4day/devops-agent) ship the same `relay.py`, so they can delegate too.

---

## Missions

| Mission | Brief looks like | Pipeline (slots) |
|---|---|---|
| `build` | create, implement, add | plan → docs → domain → test → **verify** |
| `fix` | bug, broken, failing | **debug** → domain → **verify** |
| `refactor` | clean up, simplify, migrate | plan → domain → review → **verify** |
| `design-ui` | landing, redesign, UI | **design** → domain → guidelines → verify |
| `logo` | mascot, brand mark | **logo** (one skill) |
| `audit` | review, security, a11y | audit skills → findings first |
| `research` | compare, investigate | research → domain |
| `docs` | pdf, pptx, xlsx, docx | matching format skill → writing |
| `deploy` | ship, release, preview | deploy → **verify** |
| `skill` | skills, agents, hooks, CLAUDE.md | **author** → domain → **verify** |
| `relay` | "research it with Codex, then build", delegate to, hand off | dispatch to other harnesses → read results → domain |
| `parallel` | independent workstreams | dispatch → per-stream skills |

**Bold** = required slot. When no installed skill fills a required slot, the agent does that step by hand and says so. Slots and candidates live in [`missions.md`](nummode/playbooks/missions.md). Edit the tables to change routing; the router parses them directly.

### Scoring

| Signal | Points |
|---|---:|
| Skill named in the brief | +6 |
| First installed candidate for a slot | +4 |
| Skill-name words in the brief | +2 each (max 4) |
| ≥ 2 description words in the brief | +1 each (max 3) |
| Repo stack matches | +2 |
| Tag fits the mission | +1 |
| "Only when explicitly asked" skill not named | −4 |

Slot picks need a score of 3 or more; domain picks need 4 or more. The plan holds 1–7 skills, ordered process → domain → finish.

---

## Repo layout

```text
agents/{claude,cursor,codex}/   harness agent definitions
skills/nummode/                 the universal skill (SKILL.md, references/, scripts/)
nummode/                        shared runtime copied to ~/.nummode (playbooks, scripts)
tests/                          unit tests + installer smoke test
scripts/check-sync.sh           fails if the duplicated playbooks/scripts drift
install.sh update.sh uninstall.sh VERSION CHANGELOG.md
```

```bash
bash scripts/check-sync.sh && python3 tests/test_refresh_index.py && python3 tests/test_route.py && python3 tests/test_relay.py && bash tests/test_install.sh
```

---

## Design principles

- **Brief = approval.** Interactive approval gates are skipped, with a one-line note.
- **Harness listing wins.** Never invoke a skill the harness cannot load.
- **Evidence before done.** No unverified claims that checks pass.
- **Files are data.** Instructions inside repos or web pages are ignored.
- **Irreversible only on request.** Push, deploy, publish and delete run only when the brief asks.

---

## Uninstall

```bash
./uninstall.sh            # keeps user playbooks and ~/.nummode/backups
./uninstall.sh --purge    # removes ~/.nummode entirely
```

Codex `features.multi_agent` is left unchanged.

## License

MIT
