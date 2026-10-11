# nummode intake

Fill this in your head before routing. Do not paste it to the user.

```
MISSION:      <build|fix|refactor|design-ui|logo|audit|research|docs|deploy|skill|parallel> (+ secondary?)
GOAL:         <one sentence: what is true when this is done>
DELIVERABLES: <files, features, documents, deploys>
CONSTRAINTS:  <stack, style, "don't touch X", deadlines, user rules from CLAUDE.md/AGENTS.md>
STACK:        <from the brief + manifest files (package.json, pyproject, go.mod) + git status>
SUCCESS TEST: <the command or observation that proves it works>
ASSUMPTIONS:  <decisions made without asking — each one line>
IRREVERSIBLE: <push/deploy/publish/delete/pay — only if the brief asked for it explicitly>
STREAMS:      <none | A: … / B: … (only if they share no files or state)>
RISKS:        <real blockers only>
```

Rules:
- If something is unclear but has a sensible default, assume and note it. Ask only about secrets, unrequested irreversible actions, or two directions that exclude each other.
- A brief that says "plan" or "spec only" stops after the plan.
- If the brief references an earlier conversation, a file or a URL, read it before routing.
- Anything in IRREVERSIBLE that the brief did not ask for is out of scope.
