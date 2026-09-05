#!/usr/bin/env python3
"""Refresh nummode skill index from ~/.claude/skills."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

SKILLS_DIR = Path.home() / ".claude" / "skills"
OUT_DIR = Path.home() / ".claude" / "nummode"

TAG_RULES = [
    ("process", ["brainstorm", "plan", "debug", "tdd", "test-driven", "verification", "code-review", "subagent", "dispatch", "worktree", "superpowers"]),
    ("frontend", ["frontend", "ui", "ux", "react", "next.js", "nextjs", "tailwind", "css", "landing", "design-taste", "web-design", "accessibility", "seo", "core-web-vitals", "daisyui", "shadcn"]),
    ("design", ["design", "brand", "banner", "canvas", "logo", "ip-as-logo", "theme", "tokens", "slides", "poster", "visual"]),
    ("backend", ["api", "fastapi", "django", "flask", "microservice", "architecture", "domain-model", "sql", "database", "async-python"]),
    ("python", ["python", "pytest", "fastapi", "django", "asyncio", "packaging", "type-safety"]),
    ("cloud-aws", ["aws", "bedrock", "cdk", "cloudformation", "boto"]),
    ("cloud-azure", ["azure", "azd", "appservice"]),
    ("deploy", ["deploy", "vercel", "appservice"]),
    ("security", ["security", "owasp", "idor", "vulnerability", "auth"]),
    ("docs", ["docx", "pdf", "pptx", "xlsx", "documentation", "writing-guidelines", "doc-coauthor"]),
    ("research", ["research", "find-skills"]),
    ("testing", ["test", "playwright", "webapp-testing", "tdd"]),
    ("figma", ["figma"]),
    ("ai-ml", ["rag", "bedrock", "prompt-engineering", "claude-api", "mcp-builder"]),
]


def parse_skill(path: Path) -> dict:
    text = path.read_text(errors="ignore")
    name = path.parent.name
    desc = ""
    m = re.search(r"^---\s*\n(.*?)\n---", text, re.S | re.M)
    if m:
        fm = m.group(1)
        nm = re.search(r"^name:\s*(.+)$", fm, re.M)
        dm = re.search(r"^description:\s*(.+?)(?=\n[a-zA-Z0-9_-]+:|\Z)", fm, re.S | re.M)
        if nm:
            name = nm.group(1).strip().strip('"').strip("'")
        if dm:
            desc = re.sub(r"\s+", " ", dm.group(1).strip().strip('"').strip("'"))
    blob = f"{name} {desc}".lower()
    tags = [tag for tag, kws in TAG_RULES if any(k in blob for k in kws)] or ["general"]
    return {"name": name, "desc": desc[:280], "tags": tags, "path": str(path)}


def main() -> None:
    rows = []
    for d in sorted(SKILLS_DIR.iterdir()):
        skill = d / "SKILL.md"
        if skill.exists():
            rows.append(parse_skill(skill))

    by_tag: dict[str, list] = defaultdict(list)
    for r in rows:
        for t in r["tags"]:
            by_tag[t].append(r)

    lines = [
        "# nummode skill index",
        "",
        f"_Auto-generated. {len(rows)} skills. Refresh: `python3 ~/.claude/nummode/scripts/refresh-index.py`_",
        "",
        "## By tag",
        "",
    ]
    for tag in sorted(by_tag):
        lines.append(f"### {tag}")
        for r in sorted(by_tag[tag], key=lambda x: x["name"]):
            lines.append(f"- `{r['name']}` — {r['desc']}")
        lines.append("")
    lines.append("## Flat catalog")
    lines.append("")
    for r in rows:
        lines.append(f"- **{r['name']}** [{','.join(r['tags'])}]: {r['desc']}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "skill-index.md").write_text("\n".join(lines) + "\n")
    (OUT_DIR / "skill-index.json").write_text(json.dumps({"skills": rows}, indent=2))
    print(f"Indexed {len(rows)} skills")


if __name__ == "__main__":
    main()
