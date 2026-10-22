#!/usr/bin/env python3
"""Rank installed skills for a brief and print the nummode skill plan.

Usage:
  route.py "build a stripe checkout page in next.js and deploy it"
  route.py --file brief.md            # long briefs
  echo "fix the failing login test" | route.py -
  route.py --mission audit --harness claude --json "<brief>"

It refreshes ~/.nummode/skill-index.json when skills changed on disk, detects the
mission from missions.md signals, fills the mission's slots with installed
skills, and adds domain skills that match the brief and the repo stack.
The output is a recommendation: the agent still reads each skill before use.
"""
from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_SKILLS = 7
KEEP_AT = 3          # minimum score for a slot pick
DOMAIN_AT = 4        # domain picks need a little more evidence

STOPWORDS = set("""
a an and any are as at be been but by can could do does for from get has have how i if in into is it its
just let like make me my need needs not now of on or our out please should so some than that the their them
then there these this those to up us use used uses using want was we were what when where which while who will
with without would you your all also more most new one only own same such very via each every other via etc
skill skills guidance expert help helps task tasks work working code best practices patterns things thing
tool tools user users trigger triggers file files when doing asked asks any including covers based
""".split())

# Present in most repos; never a reason to pick a skill on their own.
GENERIC_STACK = {"node", "github", "python", "docker"}

HARNESS_SOURCES = {
    "claude": ("claude", "plugin:"),
    "cursor": ("cursor", "agents"),
    "codex": ("codex", "agents"),
    "gemini": ("gemini", "antigravity", "agents"),
}

EXPLICIT_ONLY_RE = re.compile(
    r"(trigger|use) only when (the )?user (explicitly )?(asks|requests)|only when the user explicitly|"
    r"do not trigger for", re.I)


def _load_indexer():
    spec = importlib.util.spec_from_file_location("nummode_refresh_index", HERE / "refresh-index.py")
    if spec is None or spec.loader is None:
        raise SystemExit("error: refresh-index.py not found next to route.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- text helpers

def stem(tok: str) -> str:
    """Tiny suffix stripper so test/tests/testing and deploy/deploying meet."""
    if "." in tok or "+" in tok or "#" in tok:
        return tok
    for suf in ("ing", "ed"):
        if len(tok) > len(suf) + 3 and tok.endswith(suf):
            return tok[: -len(suf)]
    if len(tok) > 4 and tok.endswith("es") and tok[-3] in "sxz":
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith(("ss", "us", "is")):
        return tok[:-1]
    return tok


def tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-z0-9][a-z0-9.+#]*", text.lower().replace("-", " ").replace("_", " "))
    out = set()
    for t in raw:
        t = t.rstrip(".")
        if len(t) < 2 or t in STOPWORDS or t.isdigit():
            continue
        out.add(stem(t))
    return out


def has_phrase(text: str, phrase: str) -> bool:
    phrase = phrase.lower().strip()
    if not phrase:
        return False
    # Whole words, allowing plural / -ing / -ed: "check" matches "checks" but never "checkout".
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?:s|es|ed|ing)?(?![a-z0-9])", text) is not None


# ---------------------------------------------------------------- missions.md

@dataclass
class Slot:
    name: str
    need: str
    max: int
    candidates: list[str]


@dataclass
class Mission:
    name: str
    signals: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    slots: list[Slot] = field(default_factory=list)


def find_missions_file() -> Path:
    env = os.environ.get("NUMMODE_MISSIONS")
    options = [Path(env)] if env else []
    options += [HERE.parent / "playbooks" / "missions.md", HERE.parent / "references" / "missions.md",
                Path.home() / ".nummode" / "playbooks" / "missions.md"]
    for p in options:
        if p.is_file():
            return p
    raise SystemExit("error: missions.md not found (reinstall nummode)")


def parse_missions(text: str) -> dict[str, Mission]:
    missions: dict[str, Mission] = {}
    cur: Mission | None = None
    for line in text.splitlines():
        m = re.match(r"^###\s+`([a-z][a-z0-9-]*)`", line)
        if m:
            cur = Mission(m.group(1))
            missions[cur.name] = cur
            continue
        if line.startswith("## "):
            cur = None
            continue
        if cur is None:
            continue
        if line.startswith("Signals:"):
            cur.signals = [s.strip().lower() for s in line.split(":", 1)[1].split(",") if s.strip()]
        elif line.startswith("Tags:"):
            cur.tags = [s.strip().lower() for s in line.split(":", 1)[1].split(",") if s.strip()]
        elif line.startswith("|") and not re.match(r"^\|\s*(Slot|-)", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 4 and cells[1] in {"required", "optional", "match"}:
                cur.slots.append(Slot(cells[0], cells[1], int(cells[2]),
                                      [c.strip() for c in cells[3].split(",") if c.strip()]))
    return missions


# ---------------------------------------------------------------- repo stack

def detect_stack(repo: Path) -> set[str]:
    stack: set[str] = set()
    pkg = repo / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text())
            for sec in ("dependencies", "devDependencies"):
                for dep in (data.get(sec) or {}):
                    base = dep.split("/")[-1] if dep.startswith("@") else dep
                    stack.update(tokens(base))
                    if dep.startswith("@"):
                        stack.update(tokens(dep.split("/")[0].lstrip("@")))
        except (OSError, ValueError, AttributeError):
            pass
        stack.add("node")
    for name in ("pyproject.toml", "requirements.txt"):
        p = repo / name
        if p.is_file():
            try:
                txt = p.read_text(errors="ignore").lower()
            except OSError:
                continue
            stack.add("python")
            for lib in ("django", "fastapi", "flask", "pytest", "sqlalchemy", "pydantic", "celery", "anthropic", "openai"):
                if lib in txt:
                    stack.add(lib)
    for marker, tok in (("vercel.json", "vercel"), ("supabase", "supabase"), ("Dockerfile", "docker"),
                        (".github/workflows", "github"), ("next.config.js", "next"), ("next.config.ts", "next"),
                        ("next.config.mjs", "next"), ("go.mod", "go"), ("Cargo.toml", "rust")):
        if (repo / marker).exists():
            stack.add(tok)
    if "next" in stack:
        stack.add("next.js")
    return stack


# ---------------------------------------------------------------- routing

def detect_missions(brief: str, missions: dict[str, Mission]) -> list[tuple[str, int, list[str]]]:
    text = brief.lower()
    # Tie-break order. deploy/parallel lose ties: "build X and deploy it" is a build with a deploy tail.
    priority = ["fix", "logo", "docs", "audit", "refactor", "skill", "design-ui", "research", "build", "deploy", "relay", "parallel"]
    order = {name: i for i, name in enumerate(priority)}
    scored = []
    for m in missions.values():
        hits = [s for s in m.signals if has_phrase(text, s)]
        if hits:
            scored.append((m.name, len(hits), hits))
    scored.sort(key=lambda x: (-x[1], order.get(x[0], 99)))
    return scored


def candidate_matches(pattern: str, name: str) -> bool:
    base = name.split(":", 1)[-1]
    pattern = pattern.lower()
    return fnmatch.fnmatchcase(name.lower(), pattern) or fnmatch.fnmatchcase(base.lower(), pattern)


def harness_ok(skill: dict, harness: str) -> bool:
    if harness == "any":
        return True
    allowed = HARNESS_SOURCES[harness]
    return any(src == a or (a.endswith(":") and src.startswith(a)) for src in skill["found_in"] for a in allowed)


def base_score(skill: dict, brief_text: str, brief_toks: set[str], mission: Mission, stack: set[str]) -> tuple[int, list[str], int]:
    """Returns (score, reasons, keyword_points)."""
    name = skill["name"].lower()
    basename = name.split(":", 1)[-1]
    reasons: list[str] = []
    score = 0

    explicit = has_phrase(brief_text, name) or (
        (len(basename) >= 6 or "-" in basename) and
        (has_phrase(brief_text, basename) or has_phrase(brief_text, basename.replace("-", " "))))
    if explicit:
        score += 6
        reasons.append("named in brief")

    name_toks = tokens(basename)
    desc_toks = tokens(skill.get("desc", "")) - name_toks
    name_hits = sorted(name_toks & brief_toks)
    desc_hits = sorted(desc_toks & brief_toks)
    # One shared description word is noise ("review", "report"); two or more is signal.
    desc_pts = min(3, len(desc_hits)) if len(desc_hits) >= 2 else 0
    kw = min(4, 2 * len(name_hits)) + desc_pts
    if kw:
        score += kw
        words = name_hits + desc_hits[:3]
        reasons.append("kw: " + ", ".join(words))

    if set(skill.get("tags", [])) & set(mission.tags):
        score += 1
        reasons.append("tag")

    # Stack counts when the skill is named after it, or the brief already matched it.
    stack_hits = (name_toks & stack) or (
        {s for s in stack if len(s) > 3 and s not in GENERIC_STACK and has_phrase(skill.get("desc", "").lower(), s)}
        if kw else set())
    if stack_hits:
        score += 2
        reasons.append("stack: " + ", ".join(sorted(stack_hits)[:2]))

    if not explicit and EXPLICIT_ONLY_RE.search(skill.get("desc", "")):
        if not name_hits:
            score -= 4
            reasons.append("explicit-only")
    return score, reasons, kw + (6 if explicit else 0)


def merged_slots(primary: Mission, secondaries: list[Mission]) -> list[Slot]:
    slots = list(primary.slots)
    names = {s.name for s in slots}
    tail = [slots.pop()] if slots and slots[-1].name == "verify" else []
    for sec in secondaries:
        for s in sec.slots:
            if s.name not in names and s.candidates != ["*"]:
                slots.append(s)
                names.add(s.name)
    return slots + tail


def route(brief: str, *, index: list[dict], missions: dict[str, Mission], mission: str | None = None,
          harness: str = "any", repo: Path | None = None, limit: int = MAX_SKILLS) -> dict:
    brief_text = brief.lower()
    brief_toks = tokens(brief)
    word_count = len(brief.split())
    detected = detect_missions(brief, missions)

    if mission:
        if mission not in missions:
            raise SystemExit(f"error: unknown mission '{mission}'. Known: {', '.join(missions)}")
        primary = mission
    else:
        primary = detected[0][0] if detected else "build"
    top_hits = next((h for n, h, _ in detected if n == primary), 0)
    secondary = [n for n, h, _ in detected
                 if n != primary and n != "parallel" and (h == top_hits or h >= max(2, (top_hits + 1) // 2))][:2]

    pm = missions[primary]
    stack = detect_stack(repo) if repo else set()
    pool = [s for s in index if s["name"] != "nummode" and harness_ok(s, harness)]

    scored = {}
    for s in pool:
        sc, why, kw = base_score(s, brief_text, brief_toks, pm, stack)
        scored[s["name"]] = {"skill": s, "score": sc, "reasons": why, "kw": kw}

    slots = merged_slots(pm, [missions[n] for n in secondary])
    slot_owned = {s["name"] for s in pool
                  for sl in slots if sl.candidates != ["*"]
                  for c in sl.candidates if candidate_matches(c, s["name"])}

    picks: list[dict] = []
    gaps: list[str] = []
    taken: set[str] = set()

    for sl in slots:
        if sl.candidates == ["*"]:
            domain = sorted(
                (v for k, v in scored.items() if k not in taken and k not in slot_owned and v["score"] >= DOMAIN_AT and v["kw"] > 0),
                key=lambda v: (-v["score"], v["skill"]["name"]))
            design_count = sum(1 for p in picks if "design" in p["tags"])
            n = 0
            for v in domain:
                if n >= sl.max:
                    break
                if "design" in v["skill"]["tags"]:
                    if design_count >= 3:
                        continue
                    design_count += 1
                picks.append(_pick(v, sl.name, v["score"], v["reasons"]))
                taken.add(v["skill"]["name"])
                n += 1
            continue

        ordered = []
        for c in sl.candidates:
            for name, v in scored.items():
                if name not in taken and candidate_matches(c, name) and v not in ordered:
                    ordered.append(v)
        if sl.need == "match":
            ordered = [v for v in ordered if v["kw"] > 0]
        if not ordered:
            if sl.need == "required":
                gaps.append(sl.name)
            continue
        bonus_first = 4 if (sl.need != "optional" or word_count >= 40) else 2
        ranked = []
        for i, v in enumerate(ordered):
            bonus = bonus_first if i == 0 else 1
            ranked.append((v["score"] + bonus, i, v, bonus))
        if sl.need == "match":
            ranked.sort(key=lambda x: (-x[0], x[1]))
        for total, _, v, bonus in ranked[: sl.max]:
            if total < KEEP_AT:
                continue
            picks.append(_pick(v, sl.name, total, v["reasons"] + [f"slot {sl.name} +{bonus}"]))
            taken.add(v["skill"]["name"])
        if sl.need == "required" and not any(p["slot"] == sl.name for p in picks):
            gaps.append(sl.name)

    if len(picks) > limit:
        keep = sorted(picks, key=lambda p: (p["slot"] not in ("verify", "debug", "author", "design", "logo"), -p["score"]))[:limit]
        picks = [p for p in picks if p in keep]

    considered = sorted(
        (v for k, v in scored.items() if k not in taken and v["score"] >= 2),
        key=lambda v: (-v["score"], v["skill"]["name"]))[:5]

    names = [p["name"] for p in picks]
    return {
        "announce": f"nummode · {primary}{'+' + '+'.join(secondary) if secondary else ''} · skills: {', '.join(names) or '(none installed — proceed manually)'}",
        "mission": primary,
        "secondary": secondary,
        "signals": next((hits for n, _, hits in detected if n == primary), []),
        "skills": picks,
        "gaps": gaps,
        "considered": [{"name": v["skill"]["name"], "score": v["score"]} for v in considered],
        "stack": sorted(stack),
        "harness": harness,
    }


def _pick(v: dict, slot: str, score: int, reasons: list[str]) -> dict:
    s = v["skill"]
    return {"name": s["name"], "slot": slot, "score": score, "reasons": reasons,
            "tags": s.get("tags", []), "path": s.get("path", "")}


def default_harness() -> str:
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude"
    if os.environ.get("CODEX_HOME") or os.environ.get("CODEX_SANDBOX"):
        return "codex"
    if os.environ.get("CURSOR_TRACE_ID") or os.environ.get("CURSOR_AGENT"):
        return "cursor"
    return "any"


def render(plan: dict, index_note: str) -> str:
    out = [plan["announce"], ""]
    sig = ", ".join(plan["signals"]) or "none (default)"
    out.append(f"mission: {plan['mission']} (signals: {sig})"
               + (f" · secondary: {', '.join(plan['secondary'])}" if plan["secondary"] else ""))
    for i, p in enumerate(plan["skills"], 1):
        out.append(f"  {i}. {p['name']:<34} [{p['slot']}] score {p['score']:>2} · {'; '.join(p['reasons'])}")
    if not plan["skills"]:
        out.append("  (no installed skill scored ≥3)")
    for g in plan["gaps"]:
        out.append(f"gap: no installed skill for required slot `{g}`; do this step by hand and say so")
    if plan["considered"]:
        out.append("also considered: " + ", ".join(f"{c['name']} ({c['score']})" for c in plan["considered"]))
    if plan["stack"]:
        out.append("stack: " + ", ".join(plan["stack"][:12]))
    out.append(f"harness: {plan['harness']} · index: {index_note}")
    out.append("next: read each skill's SKILL.md (Skill tool in Claude Code) before the work it covers")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brief", nargs="*", help="the brief text, or - for stdin")
    ap.add_argument("--file", "-f", type=Path, help="read the brief from a file")
    ap.add_argument("--mission", "-m", help="force a mission")
    ap.add_argument("--harness", choices=["any", *HARNESS_SOURCES], default=None,
                    help="only skills this harness can load (default: auto-detect)")
    ap.add_argument("--repo", type=Path, default=Path.cwd(), help="repo to read stack hints from (default: cwd)")
    ap.add_argument("--limit", type=int, default=MAX_SKILLS)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-refresh", action="store_true", help="use the saved index even if stale")
    args = ap.parse_args(argv)

    if args.file:
        brief = args.file.read_text(errors="ignore")
    elif args.brief == ["-"] or (not args.brief and not sys.stdin.isatty()):
        brief = sys.stdin.read()
    else:
        brief = " ".join(args.brief)
    if not brief.strip():
        ap.error("empty brief")

    indexer = _load_indexer()
    if args.no_refresh and (saved := indexer.load_saved()):
        index, note = saved.get("skills", []), f"saved ({saved.get('generated', '?')})"
    else:
        fresh, reason, rows = indexer.is_fresh()
        if not fresh:
            try:
                indexer.write_index()
                note = f"refreshed ({reason})"
            except OSError as e:
                note = f"stale, refresh failed: {e}"
        else:
            note = reason
        index = rows

    missions = parse_missions(find_missions_file().read_text())
    plan = route(brief, index=index, missions=missions, mission=args.mission,
                 harness=args.harness or default_harness(), repo=args.repo, limit=max(1, args.limit))
    plan["index"] = note
    print(json.dumps(plan, indent=2) if args.json else render(plan, note))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
