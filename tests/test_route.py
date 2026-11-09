#!/usr/bin/env python3
"""Tests for the nummode router and the missions.md contract."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "nummode" / "scripts" / "route.py"
MISSIONS_MD = ROOT / "nummode" / "playbooks" / "missions.md"


def load_mod():
    spec = importlib.util.spec_from_file_location("route", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["route"] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


R = load_mod()
MISSIONS = R.parse_missions(MISSIONS_MD.read_text())


def sk(name, desc, tags=("general",), found=("claude",)):
    return {"name": name, "desc": desc, "tags": list(tags), "found_in": list(found), "path": f"/x/{name}/SKILL.md"}


INDEX = [
    sk("systematic-debugging", "Find root causes before fixing bugs, test failures or unexpected behavior.", ["process"]),
    sk("verification-before-completion", "Run verification commands before claiming work is complete.", ["process"]),
    sk("writing-plans", "Turn a spec into a step-by-step implementation plan.", ["process"]),
    sk("frontend-design", "Distinctive visual design for UI, typography and aesthetic direction.", ["design", "frontend"]),
    sk("web-design-guidelines", "Review UI code for accessibility and interface guidelines.", ["frontend"]),
    sk("supabase", "Use for Supabase auth, database, RLS, storage and edge functions.", ["data", "backend"]),
    sk("supabase-postgres-best-practices", "Postgres schema, RLS policies, indexes and migrations.", ["data"]),
    sk("security-best-practices", "Security review of code. Trigger only when the user explicitly requests security review.", ["security"]),
    sk("pdf", "Create, merge, split and fill PDF files.", ["docs"]),
    sk("pptx", "Create slide decks and presentations as pptx.", ["docs"]),
    sk("ip-as-logo", "Design a mascot or IP character logo.", ["design"]),
    sk("vercel:deploy", "Deploy the current project to Vercel preview or production.", ["deploy"], ["plugin:vercel"]),
    sk("cursor-only", "Frontend ui react design work.", ["frontend"], ["cursor"]),
    sk("nummode", "Autonomous skill OS.", ["skills"]),
]


def plan(brief, **kw):
    return R.route(brief, index=INDEX, missions=MISSIONS, **kw)


class MissionsFileTests(unittest.TestCase):
    EXPECTED = {"build", "fix", "refactor", "design-ui", "logo", "audit", "research", "docs", "deploy", "skill", "relay", "parallel"}

    def test_all_missions_parse_with_signals_tags_slots(self):
        self.assertEqual(set(MISSIONS), self.EXPECTED)
        for m in MISSIONS.values():
            self.assertTrue(m.signals, m.name)
            self.assertTrue(m.tags, m.name)
            self.assertTrue(m.slots, m.name)
            for s in m.slots:
                self.assertIn(s.need, {"required", "optional", "match"})
                self.assertGreaterEqual(s.max, 1)

    def test_code_missions_end_with_required_verify(self):
        for name in ("build", "fix", "refactor", "deploy", "skill"):
            last = MISSIONS[name].slots[-1]
            self.assertEqual((last.name, last.need), ("verify", "required"), name)

    def test_every_surface_lists_every_mission(self):
        surfaces = {
            "SKILL.md": (ROOT / "skills/nummode/SKILL.md").read_text(),
            "claude agent": (ROOT / "agents/claude/nummode.md").read_text(),
            "cursor agent": (ROOT / "agents/cursor/nummode.md").read_text(),
            "codex agent": tomllib.loads((ROOT / "agents/codex/nummode.toml").read_text())["developer_instructions"],
            "README": (ROOT / "README.md").read_text(),
        }
        for label, text in surfaces.items():
            for mission in self.EXPECTED:
                self.assertRegex(text, rf"(?<![a-z-]){re.escape(mission)}(?![a-z-])", f"{label} missing {mission}")

    def test_frontmatter_is_valid(self):
        text = (ROOT / "skills/nummode/SKILL.md").read_text()
        fm = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        self.assertIsNotNone(fm)
        self.assertRegex(fm.group(1), r"(?m)^name: nummode$")
        self.assertLess(len(fm.group(1)), 1024)


class DetectTests(unittest.TestCase):
    def mission(self, brief):
        return plan(brief)["mission"]

    def test_detection(self):
        cases = {
            "The checkout button is broken and throws an error": "fix",
            "Build a todo app with a REST endpoint": "build",
            "Redesign the landing page hero": "design-ui",
            "Design a mascot logo for our brand": "logo",
            "Security audit of the payments service": "audit",
            "Compare Postgres vs MySQL for our workload": "research",
            "Turn these notes into a pptx deck": "docs",
            "Deploy the app to production": "deploy",
            "Refactor the auth module and simplify it": "refactor",
            "Improve my nummode skill and its agent hooks": "skill",
            "hello": "build",
        }
        for brief, expected in cases.items():
            self.assertEqual(self.mission(brief), expected, brief)

    def test_forced_mission(self):
        self.assertEqual(plan("anything", mission="audit")["mission"], "audit")
        with self.assertRaises(SystemExit):
            plan("anything", mission="nope")


class RouteTests(unittest.TestCase):
    def names(self, brief, **kw):
        return [s["name"] for s in plan(brief, **kw)["skills"]]

    def test_fix_pipeline_order(self):
        self.assertEqual(self.names("login test is failing, fix the bug")[0], "systematic-debugging")
        self.assertEqual(self.names("login test is failing, fix the bug")[-1], "verification-before-completion")

    def test_domain_skill_from_keywords(self):
        names = self.names("add RLS policies to the postgres orders table")
        self.assertIn("supabase-postgres-best-practices", names)
        self.assertEqual(names[-1], "verification-before-completion")

    def test_named_skill_wins(self):
        self.assertIn("supabase", self.names("build signup using supabase auth"))

    def test_explicit_only_penalty(self):
        self.assertNotIn("security-best-practices", self.names("build a blog with markdown posts"))
        self.assertIn("security-best-practices", self.names("security review of the login code"))

    def test_docs_match_slot_picks_only_requested_format(self):
        names = self.names("make a pdf report from this csv")
        self.assertIn("pdf", names)
        self.assertNotIn("pptx", names)

    def test_logo_is_one_skill(self):
        self.assertEqual(self.names("design a mascot logo"), ["ip-as-logo"])

    def test_never_routes_to_itself(self):
        self.assertNotIn("nummode", self.names("use nummode to build a nummode skill"))

    def test_harness_filter(self):
        self.assertNotIn("cursor-only", self.names("frontend react ui design work", harness="claude"))
        self.assertIn("vercel:deploy", self.names("deploy to vercel production", harness="claude"))
        self.assertNotIn("vercel:deploy", self.names("deploy to vercel production", harness="codex"))
        # Cursor also loads Claude/Codex skill directories (compat).
        self.assertIn("systematic-debugging", self.names("fix the crash", harness="cursor"))
        self.assertIn("cursor-only", self.names("frontend react ui design work", harness="cursor"))

    def test_gap_reported_when_required_slot_empty(self):
        idx = [s for s in INDEX if s["name"] != "verification-before-completion"]
        p = R.route("fix the crash", index=idx, missions=MISSIONS)
        self.assertIn("verify", p["gaps"])

    def test_limit(self):
        p = plan("build supabase postgres rls frontend design pdf deploy vercel", mission="build", limit=2)
        self.assertLessEqual(len(p["skills"]), 2)
        self.assertIn("verification-before-completion", [s["name"] for s in p["skills"]])

    def test_secondary_mission(self):
        p = plan("build the api, then deploy it to production and release a preview")
        self.assertIn("deploy", [p["mission"], *p["secondary"]])

    def test_build_then_deploy_is_build_with_deploy_secondary(self):
        p = plan("build a stripe checkout in next.js and deploy it")
        self.assertEqual(p["mission"], "build")
        self.assertIn("deploy", p["secondary"])
        self.assertIn("vercel:deploy", [s["name"] for s in plan("build the site and deploy it to vercel")["skills"]])

    def test_announce_line(self):
        self.assertRegex(plan("fix the crash")["announce"], r"^nummode · fix · skills: ")


class StackTests(unittest.TestCase):
    def test_package_json_and_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "package.json").write_text(json.dumps({"dependencies": {"next": "15", "@supabase/ssr": "1"}}))
            (repo / "pyproject.toml").write_text('dependencies = ["fastapi"]')
            stack = R.detect_stack(repo)
            for tok in ("next", "next.js", "supabase", "fastapi", "python", "node"):
                self.assertIn(tok, stack)

    def test_bad_package_json_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "package.json").write_text("{oops")
            self.assertIn("node", R.detect_stack(Path(tmp)))


class CliTests(unittest.TestCase):
    def test_cli_end_to_end_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            d = home / ".claude" / "skills" / "systematic-debugging"
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("---\nname: systematic-debugging\ndescription: Debug bugs and failures.\n---\n")
            env = {**os.environ, "HOME": str(home), "NUMMODE_HOME": str(home / ".nummode"), "NUMMODE_EXTRA_ROOTS": ""}
            # Parent Cursor/Claude/Codex sessions leak harness env; isolate the fake $HOME.
            for k in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CODEX_HOME", "CODEX_SANDBOX",
                      "CURSOR_TRACE_ID", "CURSOR_AGENT"):
                env.pop(k, None)
            out = subprocess.run([sys.executable, str(SCRIPT), "--json", "--harness", "any", "--repo", tmp,
                                  "the build is failing, fix it"], capture_output=True, text=True, env=env, check=True)
            data = json.loads(out.stdout)
            self.assertEqual(data["mission"], "fix")
            self.assertEqual(data["skills"][0]["name"], "systematic-debugging")
            self.assertIn("verify", data["gaps"])
            self.assertTrue((home / ".nummode" / "skill-index.json").is_file())
            # stdin + text mode (auto harness). Also prove Cursor sessions still see ~/.claude skills.
            out = subprocess.run([sys.executable, str(SCRIPT), "-"], input="fix the crash", capture_output=True,
                                 text=True, env=env, check=True)
            self.assertTrue(out.stdout.startswith("nummode · fix · skills: systematic-debugging"), out.stdout)
            env_cursor = {**env, "CURSOR_AGENT": "1"}
            out = subprocess.run([sys.executable, str(SCRIPT), "-"], input="fix the crash", capture_output=True,
                                 text=True, env=env_cursor, check=True)
            self.assertTrue(out.stdout.startswith("nummode · fix · skills: systematic-debugging"), out.stdout)

    def test_empty_brief_errors(self):
        out = subprocess.run([sys.executable, str(SCRIPT), "  "], capture_output=True, text=True,
                             stdin=subprocess.DEVNULL)
        self.assertNotEqual(out.returncode, 0)


if __name__ == "__main__":
    with mock.patch.dict(os.environ, {"CLAUDECODE": ""}):
        unittest.main(verbosity=2)
