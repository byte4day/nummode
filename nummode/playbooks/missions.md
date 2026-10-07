# nummode mission playbooks

Pick exactly one primary mission. Secondary missions allowed only if the prompt clearly demands them.

## Mission → pipeline

### `build` — create or implement something
1. `writing-plans` or `brief-to-tasks` (if multi-step) — skip interactive brainstorming approval; the pasted prompt IS the brief
2. Domain skills (frontend/backend/cloud/docs as matched)
3. `tdd` / `test-driven-development` when shipping code with testable behavior
4. `verification-before-completion` before claiming done
5. `requesting-code-review` for large code changes

### `fix` — bug, failure, unexpected behavior
1. `systematic-debugging` first (mandatory)
2. Domain skill for the stack
3. `verification-before-completion`

### `design-ui` — visual UI / landing / redesign
1. `design-taste-frontend` or `frontend-design`
2. `ui-ux-pro-max` when interaction/IA matters
3. `web-design-guidelines` / `accessibility` near the end if shipping UI
4. Avoid stacking every design skill — max 3 design-family skills

### `logo` — mascot / IP / character mark
1. `ip-as-logo` only (do not dilute with generic design skills unless asked)

### `audit` — review / quality / security / a11y / perf
1. Matching audit skill (`security-review`, `accessibility`, `web-quality-audit`, `web-design-guidelines`, `django-perf-review`, etc.)
2. Produce findings first; fix only if the prompt asks to fix

### `research` — investigate / compare / gather facts
1. `research`
2. Optionally `find-skills` if capability gap appears mid-task

### `docs` — documents / slides / spreadsheets
1. Exact format skill: `docx` / `pdf` / `pptx` / `xlsx` / `slides`
2. `writing-guidelines` for prose-heavy deliverables

### `deploy` — ship / preview / production deploy
1. Matching deploy skill (`deploy-to-vercel`, azure deploy skills, etc.)
2. `verification-before-completion`

### `parallel` — 2+ independent workstreams in one prompt
1. `dispatching-parallel-agents` or `subagent-driven-development`
2. Split by domain; each stream gets its own skill set

## Conflict rules

| Conflict | Winner |
|---|---|
| Interactive skill wants approval vs nummode autonomy | **nummode autonomy** — treat the user prompt as approved brief |
| Process skill vs domain skill | Process decides *how*; domain decides *what* |
| Multiple overlapping design skills | Keep the single best fit + one polish skill |
| Plan-only vs ship | If prompt says "plan" / "spec only" → stop after plan; else ship |

## Scoring (internal)

For each **installed** candidate skill, score 0–5:
- +2 description keyword overlap with prompt nouns/verbs
- +3 mission playbook includes it (playbook hits clear the bar alone)
- +1 stack detected in repo/prompt (Next, Django, etc.)
- −2 weak/generic match only
- −3 duplicates another selected skill’s job

Select up to **7** skills with score ≥ 3. Prefer installed playbook steps; if a playbook name is missing, use the nearest installed equivalent (or proceed with a one-line note) — never invent or fake-invoke a skill. Always include a finisher when producing code.
