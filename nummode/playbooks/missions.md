# nummode mission playbooks

One primary mission per brief. Add a secondary mission only when the brief clearly asks for it (e.g. `build` + `deploy`).

`route.py` parses this file, so keep the format: a `### \`mission\`` heading, then `Signals:`, `Tags:`, and one slot table.

## How slots work

Each mission is a pipeline of **slots**, run top to bottom.

- **Candidates** are skill names or globs (`*deploy*`, `vercel:*`). Matching is exact, or by the part after `plugin:`. The first installed candidate fills the slot.
- **Need**
  - `required`: the slot must be filled. If no candidate is installed, do the step by hand and say so in one line (e.g. "no verification skill installed, ran `npm test` directly").
  - `optional`: fill it when a candidate is installed and the brief is big enough to need it.
  - `match`: fill it only with candidates whose name or description matches the brief (e.g. the `pdf` skill only when the brief asks for a PDF).
- **Max**: how many skills the slot can hold.
- `*` in Candidates means **domain skills**: the highest-scoring skills that match the brief, the mission tags or the repo stack.

---

### `build`
Create, implement, scaffold or add a feature.
Signals: build, create, implement, scaffold, add, feature, make, develop, wire, integrate, generate, app, endpoint, page
Tags: frontend, backend, data, ai, payments, testing

| Slot | Need | Max | Candidates |
|---|---|---|---|
| plan | optional | 1 | writing-plans, brief-to-tasks, superpowers:writing-plans |
| docs | optional | 1 | docs-first-engineering, context7, *:docs-first* |
| domain | match | 4 | * |
| test | optional | 1 | test-driven-development, tdd, superpowers:test-driven-development |
| verify | required | 1 | verification-before-completion, project-delivery-checks, superpowers:verification-before-completion, *:verification, run |

### `fix`
A bug, failure, error or regression.
Signals: bug, broken, error, failing, fails, fix, crash, regression, exception, traceback, 500, flaky, wrong, issue, debug, not working
Tags: testing, backend, frontend, git

| Slot | Need | Max | Candidates |
|---|---|---|---|
| debug | required | 1 | systematic-debugging, debugging, superpowers:systematic-debugging |
| domain | match | 3 | * |
| verify | required | 1 | verification-before-completion, project-delivery-checks, superpowers:verification-before-completion, *:verification, run |

### `refactor`
Restructure, clean up or simplify code without changing what it does.
Signals: refactor, cleanup, clean up, simplify, restructure, rename, extract, dedupe, tech debt, modernize, upgrade, migrate
Tags: process, frontend, backend, testing

| Slot | Need | Max | Candidates |
|---|---|---|---|
| plan | optional | 1 | writing-plans, superpowers:writing-plans |
| domain | match | 3 | * |
| review | optional | 1 | simplify, code-review, requesting-code-review |
| verify | required | 1 | verification-before-completion, project-delivery-checks, *:verification, run |

### `design-ui`
Visual UI work: landing pages, redesigns, components, styling.
Signals: landing, redesign, ui, ux, page, hero, layout, style, styling, theme, visual, frontend, component, beautiful, polish, dashboard
Tags: frontend, design

| Slot | Need | Max | Candidates |
|---|---|---|---|
| design | required | 1 | design-taste-frontend, frontend-design, ui-ux-pro-max |
| domain | match | 2 | * |
| guidelines | optional | 1 | web-design-guidelines, accessibility, web-quality-audit |
| verify | optional | 1 | run, *:verification, webapp-testing, project-delivery-checks |

Cap: at most 3 design-family skills in total.

### `logo`
A logo, mascot, IP character or brand mark.
Signals: logo, mascot, character, brand mark, icon, wordmark, emblem
Tags: design

| Slot | Need | Max | Candidates |
|---|---|---|---|
| logo | required | 1 | ip-as-logo, logo-design, brand-identity, figma:figma-generate-design |

A single skill is enough. Do not add generic design skills unless the brief asks for them.

### `audit`
Review code or a product: quality, security, a11y, performance. Produce findings first.
Signals: review, audit, a11y, accessibility, security, vulnerability, threat, perf, performance, lighthouse, check, assess, inspect
Tags: security, testing, frontend

| Slot | Need | Max | Candidates |
|---|---|---|---|
| audit | match | 3 | security-review, security-best-practices, security-threat-model, code-review, web-design-guidelines, accessibility, web-quality-audit, vercel:performance*, django-perf-review |
| domain | match | 2 | * |

Report findings first. Fix only if the brief asks for fixes.

### `research`
Investigate, compare or gather facts. The deliverable is an answer.
Signals: research, compare, investigate, explore, find out, evaluate, which, versus, vs, options, pros, cons, survey
Tags: research, docs

| Slot | Need | Max | Candidates |
|---|---|---|---|
| research | optional | 1 | research, deep-research, docs-first-engineering |
| domain | match | 3 | * |

### `docs`
Produce a document: pdf, pptx, xlsx, docx, slides or long-form writing.
Signals: pdf, pptx, xlsx, docx, slides, deck, spreadsheet, document, report, presentation, write-up, whitepaper, readme
Tags: docs

| Slot | Need | Max | Candidates |
|---|---|---|---|
| format | match | 2 | docx, pdf, pptx, xlsx, slides, anthropic-skills:docx, anthropic-skills:pdf, anthropic-skills:pptx, anthropic-skills:xlsx, anthropic-skills:docs |
| writing | optional | 1 | writing-guidelines, doc-coauthoring |
| domain | match | 2 | * |

### `deploy`
Ship, preview, release or roll back.
Signals: deploy, ship, release, preview, production, prod, rollback, publish, go live, hosting, domain, ci/cd
Tags: deploy, cloud, git

| Slot | Need | Max | Candidates |
|---|---|---|---|
| deploy | match | 1 | deploy-to-vercel, vercel:deploy, vercel:deployments-cicd, *deploy*, *:vercel-cli |
| domain | match | 2 | * |
| verify | required | 1 | verification-before-completion, project-delivery-checks, *:verification, run |

### `skill`
Create or improve a skill, agent, plugin, hook, prompt or harness config.
Signals: skill, skills, subagent, plugin, hook, hooks, system prompt, claude.md, agents.md, settings.json, mod, slash command, update nummode, improve nummode, fix nummode
Tags: skills, ai, process

Follow [Agent Skills](https://agentskills.io/): short trigger-specific `description`, root `SKILL.md` as a router, detail in `references/`, prefer `model: inherit` / documented aliases (`fable`/`opus`/`sonnet`/`haiku`). See `models-and-harness.md`.

| Slot | Need | Max | Candidates |
|---|---|---|---|
| author | required | 1 | skill-creator, anthropic-skills:skill-creator, writing-skills, superpowers:writing-skills, plugin-authoring, update-config |
| domain | match | 2 | * |
| verify | required | 1 | verification-before-completion, project-delivery-checks, *:verification |

### `parallel`
Two or more independent deliverables in one brief.
Signals: parallel, in parallel, simultaneously, at the same time, independent streams, workstreams, separately
Tags: process

| Slot | Need | Max | Candidates |
|---|---|---|---|
| dispatch | optional | 1 | dispatching-parallel-agents, subagent-driven-development, superpowers:dispatching-parallel-agents |
| domain | match | 4 | * |

Split streams by deliverable. Give each stream its own mission and skills. Only parallelize streams that share no files or state.

### `relay`
Hand parts of the brief to other agent harnesses (Claude Code, Codex, Cursor, Antigravity/Gemini, OpenCode) and continue from their saved results.
Signals: relay, delegate to, hand off, handoff, another harness, other harness, cross-harness, worker agent, ask codex, use codex, ask cursor, use cursor, ask gemini, use gemini, use antigravity, ask antigravity, use opencode, ask claude, with codex, with cursor, with gemini, with antigravity, with opencode, in codex, in cursor, in antigravity, open codex, open cursor, launch codex, launch cursor
Tags: process

| Slot | Need | Max | Candidates |
|---|---|---|---|
| domain | match | 4 | * |

Run `python3 ~/.nummode/scripts/relay.py harnesses`, dispatch each self-contained sub-task with `relay.py dispatch --to <harness> --task "…"` (default `--mode read`; `--mode write` only for disjoint files), `relay.py wait`, then read every `.relay/<id>/result.md` before continuing. Verify worker output like any other evidence.

---

## Conflict rules

| Conflict | Winner |
|---|---|
| A skill wants interactive approval vs nummode autonomy | **nummode**: the brief is the approval; note the assumption in one line |
| Process skill vs domain skill | Process decides *how*; domain decides *what* |
| Two skills do the same job | Keep the higher scorer; drop the other (−3) |
| Several design skills | One best fit + one polish skill, never more than 3 |
| "Plan only" / "spec only" vs ship | Stop after the plan when the brief says so; otherwise ship |
| Skill says "only when explicitly asked" | Use it only when the brief names its topic |

## Scoring (what route.py computes)

Additive, per installed skill:

| Signal | Points |
|---|---:|
| Named in the brief (`use supabase`) | +6 |
| First installed candidate of a slot (`match` slots also need a keyword hit) | +4 |
| Later candidate of a slot | +1 |
| Skill name words appear in the brief | +2 each, max +4 |
| Description words appear in the brief | +1 each, max +3 |
| Tag is one of the mission's tags | +1 |
| Repo stack matches (package.json / pyproject deps) | +2 |
| Description says "only when explicitly asked" and the brief does not name it | −4 |
| Duplicates a slot that a higher scorer already filled | dropped |

Keep skills that score at least 3. Lock **1–7**, sized to the brief. Order them process → domain → finish. Never invent or fake-invoke a skill.
