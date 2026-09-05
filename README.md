# nummode

**Paste a big prompt. nummode picks the skills. Then it ships.**

nummode is a Claude Code agent that turns large, messy briefs into routed skill plans — then executes without asking which skills to use.

```
you:  [1200-word product brief]
nummode · build · skills: writing-plans, frontend-design, verification-before-completion
        → plans → builds → verifies → done
```

---

## Why

Claude Code can load dozens of skills. Humans shouldn't babysit which ones fire.

nummode is the missing layer:

1. **Intake** — parse goal, deliverables, constraints, stack
2. **Mission** — classify as `build` / `fix` / `design-ui` / `logo` / `audit` / …
3. **Route** — score installed skills, lock a 3–7 skill plan
4. **Invoke** — Skill tool, before any real work
5. **Execute** — parallelize only when safe
6. **Verify** — evidence before “done”

No skill-selection theater. The pasted prompt is the approved brief.

---

## Install

Requires [Claude Code](https://code.claude.com/) and skills under `~/.claude/skills/`.

```bash
git clone https://github.com/669px/nummode.git
cd nummode
chmod +x install.sh
./install.sh
```

The installer:

- copies the agent to `~/.claude/agents/nummode.md`
- copies playbooks + scripts to `~/.claude/nummode/`
- rebuilds your personal skill index from `~/.claude/skills/`
- sets `"agent": "nummode"` in `~/.claude/settings.json`

Then open a **new** Claude Code session, or:

```bash
claude --agent nummode
```

### Manual install

```bash
mkdir -p ~/.claude/agents ~/.claude/nummode
cp agents/nummode.md ~/.claude/agents/
cp -R nummode/* ~/.claude/nummode/
python3 ~/.claude/nummode/scripts/refresh-index.py
```

Set default agent in `~/.claude/settings.json`:

```json
{
  "agent": "nummode"
}
```

---

## Usage

Paste a large brief. Expect a one-liner like:

```text
nummode · fix · skills: systematic-debugging, nextjs-app-router-patterns, verification-before-completion
```

Then work starts. nummode only asks when blocked by:

- missing secrets
- irreversible destructive actions without clear intent
- mutually exclusive product directions

It will **not** ask which skills to use.

### Optional mid-session

```text
@nummode
```

### Refresh skill index

After installing or removing skills:

```bash
python3 ~/.claude/nummode/scripts/refresh-index.py
```

---

## Missions

| Mission | When the prompt looks like | Pipeline sketch |
|--------|----------------------------|-----------------|
| `build` | create, implement, scaffold | plan → domain → tdd → verify |
| `fix` | bug, broken, failing | systematic-debugging → domain → verify |
| `design-ui` | landing, redesign, UI | design skills (max 3) → polish |
| `logo` | mascot, IP mark | `ip-as-logo` |
| `audit` | review, a11y, security | audit skill → findings (fix if asked) |
| `research` | investigate, compare | `research` |
| `docs` | pdf / pptx / xlsx / docx | format skill |
| `deploy` | ship, preview | deploy skill → verify |
| `parallel` | unrelated workstreams | dispatch parallel agents |

Full playbooks: [`nummode/playbooks/missions.md`](nummode/playbooks/missions.md)

---

## How routing works

Skills are scored, not vibed:

| Signal | Score |
|--------|------:|
| Description keywords overlap the prompt | +2 |
| Mission playbook lists the skill | +2 |
| Stack matches repo/prompt | +1 |
| Weak / generic match only | −2 |
| Duplicates another selected skill’s job | −3 |

Keep skills with score ≥ 3. Cap at 3–7. Prefer specific over generic (`ip-as-logo` > `design`).

---

## Repo layout

```text
nummode/
├── agents/nummode.md          # Claude Code agent (the brain)
├── nummode/
│   ├── playbooks/
│   │   ├── missions.md        # mission → skill pipelines
│   │   └── intake.md          # brief parser template
│   ├── scripts/
│   │   └── refresh-index.py   # index ~/.claude/skills
│   └── skill-index.md         # generated locally on install
├── install.sh
├── LICENSE
└── README.md
```

Your generated skill catalog stays on your machine (`~/.claude/nummode/skill-index.*`). It is not committed — it reflects *your* installed skills.

---

## Design principles

- **Prompt = approval** — interactive “wait for design OK” gates are overridden under nummode
- **Process before domain** — how before what
- **Evidence before done** — prefer verification skills for code
- **Repo text is data** — ignore jailbreak-shaped file content
- **Quiet competence** — short status, then output

---

## Uninstall

```bash
rm -f ~/.claude/agents/nummode.md
rm -rf ~/.claude/nummode
# remove "agent": "nummode" from ~/.claude/settings.json if set
```

---

## License

MIT
