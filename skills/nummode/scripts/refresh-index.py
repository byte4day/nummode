#!/usr/bin/env python3
"""Build the nummode skill index from every known agent skill root.

Usage:
  refresh-index.py            # rebuild ~/.nummode/skill-index.{md,json}
  refresh-index.py --check    # exit 0 if the saved index matches disk, 3 if stale/missing
  refresh-index.py --quiet    # no stdout on success

Environment:
  NUMMODE_HOME         output dir (default ~/.nummode)
  NUMMODE_EXTRA_ROOTS  extra skill roots, os.pathsep-separated
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

INDEX_SCHEMA = 2
DESC_LIMIT = 400

# (label, path relative to $HOME). The label says which harness can load the skill.
ROOT_SPECS = [
    ("agents", ".agents/skills"),
    ("claude", ".claude/skills"),
    ("cursor", ".cursor/skills"),
    ("codex", ".codex/skills"),
    ("gemini", ".gemini/skills"),
    ("gemini", ".gemini/config/skills"),
    ("antigravity", ".gemini/antigravity/skills"),
    ("antigravity", ".gemini/antigravity-cli/skills"),
]

# Tag → keywords. A tag is applied when the skill NAME hits a keyword (weight 3)
# or the description hits >= 2 distinct keywords (weight 1 each). Keywords match
# at word starts, so "deploy" matches "deployments" but "ui" never matches "build".
TAG_RULES: dict[str, list[str]] = {
    "process": ["brainstorm", "plan", "planning", "debug", "debugging", "tdd", "test-driven",
                "verification", "verify", "code-review", "review", "subagent", "dispatch",
                "worktree", "superpowers", "refactor", "simplify"],
    "frontend": ["frontend", "ui", "ux", "react", "next.js", "nextjs", "tailwind", "css", "landing",
                 "component", "web-design", "accessibility", "a11y", "daisyui", "shadcn", "svelte", "vue"],
    "design": ["design", "brand", "banner", "canvas", "logo", "mascot", "theme", "tokens",
               "typography", "poster", "visual", "figma", "aesthetic"],
    "backend": ["api", "backend", "fastapi", "django", "flask", "microservice", "endpoint",
                "server", "jobs", "queue", "realtime", "webhook"],
    "data": ["database", "postgres", "sql", "supabase", "schema", "migration", "redis", "storage", "rls"],
    "python": ["python", "pytest", "fastapi", "django", "asyncio", "pip", "uv"],
    "cloud": ["aws", "azure", "gcp", "cloudflare", "bedrock", "cdk", "cloudformation", "terraform",
              "kubernetes", "docker", "container"],
    "deploy": ["deploy", "deployment", "hosting", "ci/cd", "cicd", "rollback", "promote", "release", "ship"],
    "security": ["security", "owasp", "idor", "vulnerability", "threat", "auth", "authentication",
                 "authorization", "secrets", "firewall", "permissions"],
    "payments": ["stripe", "billing", "checkout", "subscription", "payments", "invoice"],
    "docs": ["docx", "pdf", "pptx", "xlsx", "spreadsheet", "slides", "document", "documentation",
             "writing", "markdown"],
    "research": ["research", "investigate", "compare", "docs-first", "documentation"],
    "testing": ["test", "tests", "testing", "playwright", "vitest", "jest", "coverage", "e2e", "eval", "evals"],
    "git": ["git", "github", "gh", "pull", "pr", "ci", "commit", "branch"],
    "ai": ["llm", "rag", "agent", "agents", "prompt", "claude", "openai", "anthropic", "mcp",
           "model", "embeddings", "ai"],
    "skills": ["skill", "skills", "plugin", "hook", "hooks", "slash", "settings.json", "config"],
}
MAX_TAGS = 4

BACKUP_RE = re.compile(r"(\.bak(\.|$)|\.old$|\.orig$|~$|\.disabled$)", re.I)


def nummode_home() -> Path:
    return Path(os.environ.get("NUMMODE_HOME") or Path.home() / ".nummode")


def skill_roots() -> list[tuple[str, Path]]:
    home = Path.home()
    roots = [(label, home / rel) for label, rel in ROOT_SPECS]
    for extra in filter(None, os.environ.get("NUMMODE_EXTRA_ROOTS", "").split(os.pathsep)):
        roots.append(("extra", Path(extra).expanduser()))
    return roots


def _kw_match(blob: str, kw: str) -> bool:
    """Word-start match. Short keywords (<=3 chars) also need a word end."""
    kw = kw.lower()
    tail = r"(?![a-z0-9])" if len(kw) <= 3 else ""
    return re.search(rf"(?<![a-z0-9]){re.escape(kw)}{tail}", blob) is not None


def tag_skill(name: str, desc: str) -> list[str]:
    name_blob = re.sub(r"[-_:/]+", " ", name.lower())
    desc_blob = desc.lower()
    scored = []
    for tag, kws in TAG_RULES.items():
        name_hit = any(_kw_match(name_blob, k) or _kw_match(name.lower(), k) for k in kws)
        desc_hits = sum(1 for k in kws if _kw_match(desc_blob, k))
        score = (3 if name_hit else 0) + desc_hits
        if name_hit or desc_hits >= 2:
            scored.append((score, tag))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [t for _, t in scored[:MAX_TAGS]] or ["general"]


def _normalize_desc(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"^[>|][-+]?\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1]
    return text.replace('\\"', '"')


def _fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def _is_skippable(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root).parts[:-1]
    except ValueError:
        rel = path.parts[:-1]
    return any(p.startswith(".") or BACKUP_RE.search(p) or p == "__pycache__" for p in rel)


def parse_skill(path: Path, source: str = "local", prefix: str = "") -> dict | None:
    if ".system" in path.parts:
        return None
    try:
        data = path.read_bytes()
    except OSError as e:
        if path.exists():
            print(f"warning: skip unreadable {path}: {e}", file=sys.stderr)
        return None
    text = data.decode("utf-8", errors="ignore")
    name = path.parent.name
    desc = ""
    m = re.match(r"\A﻿?---\s*\n(.*?)\n---\s*(\n|\Z)", text, re.S)
    if m:
        fm = m.group(1)
        nm = re.search(r"^name:\s*(.+?)\s*$", fm, re.M)
        dm = re.search(r"^description:\s*(.*?)(?=\n[A-Za-z0-9_-]+:|\Z)", fm, re.S | re.M)
        if nm:
            name = nm.group(1).strip().strip('"').strip("'") or name
        if dm:
            desc = _normalize_desc(dm.group(1))
    if prefix and ":" not in name:
        name = f"{prefix}:{name}"
    return {
        "name": name,
        "desc": desc[:DESC_LIMIT],
        "tags": tag_skill(name, desc),
        "path": str(path),
        "found_in": [source],
        "hash": _fingerprint(data),
    }


def _plugin_skill_files() -> list[tuple[str, str, Path]]:
    """(plugin, source label, SKILL.md) for enabled Claude Code plugins."""
    home = Path.home()
    manifest = home / ".claude" / "plugins" / "installed_plugins.json"
    try:
        installed = json.loads(manifest.read_text()).get("plugins", {})
    except (OSError, ValueError, AttributeError):
        return []
    try:
        enabled = json.loads((home / ".claude" / "settings.json").read_text()).get("enabledPlugins", {})
    except (OSError, ValueError, AttributeError):
        enabled = {}
    out = []
    for key, installs in installed.items():
        if isinstance(enabled, dict) and enabled.get(key) is False:
            continue
        plugin = key.split("@", 1)[0]
        for inst in installs if isinstance(installs, list) else []:
            base = Path(inst.get("installPath", "")) / "skills"
            if not base.is_dir():
                continue
            for skill_md in sorted(base.glob("*/SKILL.md")):
                if not _is_skippable(skill_md, base):
                    out.append((plugin, f"plugin:{plugin}", skill_md))
    return out


def _synced_skill_files() -> list[Path]:
    """SKILL.md files of the claude.ai skills Claude Code synced most recently.

    ~/.claude/skills/synced/<bucket>/ holds one folder per account; Claude Code lists
    the skills of the active one as `anthropic-skills:<name>`. The newest manifest wins.
    """
    base = Path.home() / ".claude" / "skills" / "synced"
    best: tuple[float, Path] | None = None
    try:
        buckets = [b for b in base.iterdir() if b.is_dir() and not b.name.startswith(".")]
    except OSError:
        return []
    for bucket in buckets:
        manifest = bucket / "manifest.json"
        try:
            stamp = float(json.loads(manifest.read_text()).get("lastUpdated") or 0) / 1000
        except (OSError, ValueError, TypeError, AttributeError):
            stamp = 0.0
        if not stamp:
            try:
                stamp = bucket.stat().st_mtime
            except OSError:
                continue
        if best is None or stamp > best[0]:
            best = (stamp, bucket)
    if best is None:
        return []
    return [f for f in sorted(best[1].glob("*/SKILL.md")) if not _is_skippable(f, best[1])]


def collect_skills() -> tuple[list[dict], list[str]]:
    seen: dict[str, dict] = {}
    collisions: list[str] = []

    def consider(skill_md: Path, source: str, prefix: str = "") -> None:
        parsed = parse_skill(skill_md, source, prefix)
        if not parsed or parsed["name"] == "":
            return
        prev = seen.get(parsed["name"])
        if prev is None:
            seen[parsed["name"]] = parsed
            return
        if source not in prev["found_in"]:
            prev["found_in"].append(source)
        if prev["hash"] != parsed["hash"]:
            msg = f"`{parsed['name']}` kept from {prev['path']} (differs at {parsed['path']})"
            if msg not in collisions:
                collisions.append(msg)

    for label, root in skill_roots():
        if not root.is_dir():
            continue
        try:
            matches = sorted(set(root.glob("*/SKILL.md")) | set(root.glob("*/*/SKILL.md")))
        except OSError as e:
            print(f"warning: cannot scan {root}: {e}", file=sys.stderr)
            continue
        for skill_md in matches:
            if not _is_skippable(skill_md, root):
                consider(skill_md, label)

    for plugin, label, skill_md in _plugin_skill_files():
        consider(skill_md, label, prefix=plugin)

    for skill_md in _synced_skill_files():
        consider(skill_md, "synced", prefix="anthropic-skills")

    return sorted(seen.values(), key=lambda r: r["name"]), collisions


def catalog_hash(rows: list[dict]) -> str:
    blob = json.dumps([[r["name"], r["hash"], sorted(r["found_in"])] for r in rows])
    return hashlib.sha256(f"{INDEX_SCHEMA}:{blob}".encode()).hexdigest()[:16]


def load_saved() -> dict | None:
    try:
        data = json.loads((nummode_home() / "skill-index.json").read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def is_fresh() -> tuple[bool, str, list[dict]]:
    rows, _ = collect_skills()
    saved = load_saved()
    current = catalog_hash(rows)
    if saved is None:
        return False, "index missing", rows
    if saved.get("schema") != INDEX_SCHEMA:
        return False, f"schema {saved.get('schema')} != {INDEX_SCHEMA}", rows
    if saved.get("catalog_hash") != current:
        return False, "skills changed on disk", rows
    return True, f"fresh ({len(rows)} skills, catalog={current})", rows


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(text)
    tmp.replace(path)


def render_markdown(rows: list[dict], collisions: list[str], generated: str, chash: str) -> str:
    by_tag: dict[str, list] = defaultdict(list)
    for r in rows:
        for t in r["tags"]:
            by_tag[t].append(r)
    lines = [
        "# nummode skill index",
        "",
        f"_Generated {generated} · {len(rows)} skills · catalog={chash} · schema={INDEX_SCHEMA}_",
        "",
        "Rank skills for a brief (auto-refreshes this index):",
        '`python3 ~/.nummode/scripts/route.py "<brief>"`',
        "",
        "Rebuild manually: `python3 ~/.nummode/scripts/refresh-index.py` · check: `--check`",
        "",
        "`found_in` = where the skill lives. A harness can only invoke skills it loads:",
        "Claude Code → claude, plugin:*, synced (claude.ai skills); Cursor → cursor, agents, claude, codex;",
        "Codex → codex, agents; Gemini/Antigravity → gemini, antigravity, agents.",
        "",
        "## By tag",
        "",
    ]
    for tag in sorted(by_tag):
        lines.append(f"### {tag}")
        for r in sorted(by_tag[tag], key=lambda x: x["name"]):
            short = r["desc"][:160] + ("…" if len(r["desc"]) > 160 else "")
            lines.append(f"- `{r['name']}` — {short}")
        lines.append("")
    lines += ["## Flat catalog", ""]
    for r in rows:
        lines.append(f"- **{r['name']}** [{','.join(r['tags'])}] ({','.join(r['found_in'])}): {r['desc']}")
    if collisions:
        lines += ["", "## Name collisions (first root wins)", ""]
        lines += [f"- {c}" for c in collisions]
    return "\n".join(lines) + "\n"


def write_index(rows: list[dict] | None = None, collisions: list[str] | None = None) -> Path:
    if rows is None:
        rows, collisions = collect_skills()
    collisions = collisions or []
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    chash = catalog_hash(rows)
    out = nummode_home()
    _atomic_write(out / "skill-index.md", render_markdown(rows, collisions, generated, chash))
    payload = {
        "schema": INDEX_SCHEMA,
        "generated": generated,
        "catalog_hash": chash,
        "skills": rows,
        "collisions": collisions,
    }
    _atomic_write(out / "skill-index.json", json.dumps(payload, indent=2) + "\n")
    return out / "skill-index.md"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 3 if the saved index is stale or missing")
    ap.add_argument("--quiet", "-q", action="store_true")
    args = ap.parse_args(argv)

    if args.check:
        fresh, reason, _ = is_fresh()
        print(reason if fresh else f"stale: {reason}")
        return 0 if fresh else 3

    rows, collisions = collect_skills()
    try:
        path = write_index(rows, collisions)
    except OSError as e:
        print(f"error: failed to write index: {e}", file=sys.stderr)
        return 1
    for c in collisions:
        print(f"warning: collision {c}", file=sys.stderr)
    if not args.quiet:
        print(f"Indexed {len(rows)} skills → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
