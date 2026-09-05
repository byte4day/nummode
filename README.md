# nummode

**Paste a big prompt. nummode picks the skills. Then it ships.**

Works on **Claude Code**, **Cursor**, and **Codex**.

```text
you:  [1200-word product brief]
nummode · build · skills: writing-plans, frontend-design, verification-before-completion
        → plans → builds → verifies → done
```

---

## Why

Agent harnesses can load dozens of skills. Humans shouldn't babysit which ones fire.

nummode is the routing layer:

1. **Intake** — goal, deliverables, constraints, stack  
2. **Mission** — `build` / `fix` / `design-ui` / `logo` / `audit` / …  
3. **Route** — score installed skills, lock a 3–7 skill plan  
4. **Invoke** — load skills before real work  
5. **Execute** — parallelize only when safe  
6. **Verify** — evidence before “done”

No skill-selection theater. The pasted prompt is the approved brief.

---

## Install

```bash
git clone https://github.com/byte4day/nummode.git
cd nummode
chmod +x install.sh
./install.sh          # Claude + Cursor + Codex
# or:
./install.sh cursor
./install.sh codex
./install.sh claude
```

### Via skills CLI

```bash
npx skills add byte4day/nummode -g -y -a cursor -a codex -a claude-code
./install.sh          # still run once for agents + ~/.nummode playbooks
```

### What gets installed

| Target | Path |
|--------|------|
| Shared data | `~/.nummode/` (playbooks, skill index, refresh script) |
| Universal skill | `~/.agents/skills/nummode` (+ links into each harness) |
| Claude agent | `~/.claude/agents/nummode.md` (default `agent`) |
| Cursor agent | `~/.cursor/agents/nummode.md` |
| Codex agent role | `~/.codex/agents/nummode.toml` |

---

## Usage

### Claude Code

```bash
claude --agent nummode
# or open a new session (installer sets default agent)
```

### Cursor

- Invoke **`@nummode`** on a large prompt, or  
- Let the **nummode** skill auto-trigger from its description on big briefs / multi-part builds

### Codex

- Use agent type / role **`nummode`** when spawning or starting a session  
- Or invoke the **nummode** skill on a large prompt  
- Installer enables `features.multi_agent = true` when missing (needed for parallel streams)

Expect:

```text
nummode · fix · skills: systematic-debugging, nextjs-app-router-patterns, verification-before-completion
```

Then work starts. It will **not** ask which skills to use.

### Refresh skill index

After adding/removing skills on any harness:

```bash
python3 ~/.nummode/scripts/refresh-index.py
```

Indexes `~/.agents/skills`, `~/.claude/skills`, `~/.cursor/skills`, and `~/.codex/skills`.

---

## Missions

| Mission | Prompt looks like | Pipeline sketch |
|--------|-------------------|-----------------|
| `build` | create, implement, scaffold | plan → domain → tdd → verify |
| `fix` | bug, broken, failing | systematic-debugging → domain → verify |
| `design-ui` | landing, redesign, UI | design skills (max 3) → polish |
| `logo` | mascot, IP mark | `ip-as-logo` |
| `audit` | review, a11y, security | audit skill → findings |
| `research` | investigate, compare | `research` |
| `docs` | pdf / pptx / xlsx / docx | format skill |
| `deploy` | ship, preview | deploy → verify |
| `parallel` | unrelated workstreams | dispatch parallel agents |

Playbooks: [`nummode/playbooks/missions.md`](nummode/playbooks/missions.md)

---

## Routing scores

| Signal | Score |
|--------|------:|
| Description keywords overlap the prompt | +2 |
| Mission playbook lists the skill | +2 |
| Stack matches repo/prompt | +1 |
| Weak / generic match only | −2 |
| Duplicates another selected skill’s job | −3 |

Keep skills with score ≥ 3. Cap at 3–7. Prefer specific over generic.

---

## Repo layout

```text
nummode/
├── agents/
│   ├── claude/nummode.md      # Claude Code main agent
│   ├── cursor/nummode.md      # Cursor subagent
│   └── codex/nummode.toml     # Codex agent role
├── skills/nummode/            # Universal Agent Skill
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
├── nummode/                   # Shared runtime files copied to ~/.nummode
│   ├── playbooks/
│   └── scripts/refresh-index.py
├── install.sh
├── LICENSE
└── README.md
```

Your generated skill catalog stays local (`~/.nummode/skill-index.*`) and is not committed.

---

## Design principles

- **Prompt = approval** — interactive “wait for design OK” gates are overridden  
- **Process before domain** — how before what  
- **Evidence before done** — prefer verification skills for code  
- **Repo text is data** — ignore jailbreak-shaped file content  
- **One brain, three harnesses** — same missions and scoring everywhere  

---

## Uninstall

```bash
rm -f ~/.claude/agents/nummode.md
rm -f ~/.cursor/agents/nummode.md
rm -f ~/.codex/agents/nummode.toml
rm -rf ~/.agents/skills/nummode
rm -f ~/.claude/skills/nummode ~/.cursor/skills/nummode ~/.codex/skills/nummode
rm -rf ~/.nummode ~/.claude/nummode
# remove "agent": "nummode" from ~/.claude/settings.json if set
```

---

## License

MIT
