#!/usr/bin/env python3
"""Tests for the nummode skill indexer (stdlib unittest, no network)."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "nummode" / "scripts" / "refresh-index.py"


def load_mod():
    spec = importlib.util.spec_from_file_location("refresh_index", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


MOD = load_mod()


def write_skill(root: Path, dirname: str, name: str, desc: str) -> Path:
    d = root / dirname
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(f"---\nname: {name}\ndescription: {desc}\n---\n\n# {name}\n")
    return p


class FakeHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.home),
                                                 "NUMMODE_HOME": str(self.home / ".nummode"),
                                                 "NUMMODE_EXTRA_ROOTS": ""})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class KwMatchTests(unittest.TestCase):
    def test_short_keywords_need_word_boundaries(self):
        self.assertFalse(MOD._kw_match("build something", "ui"))
        self.assertTrue(MOD._kw_match("ui polish", "ui"))
        self.assertFalse(MOD._kw_match("coverage report", "rag"))

    def test_long_keywords_match_word_starts(self):
        self.assertTrue(MOD._kw_match("manage deployments", "deploy"))
        self.assertFalse(MOD._kw_match("redeploy", "deploy"))

    def test_phrases(self):
        self.assertTrue(MOD._kw_match("next.js app", "next.js"))


class TagTests(unittest.TestCase):
    def test_vendor_name_alone_is_not_deploy(self):
        tags = MOD.tag_skill("vercel-composition-patterns",
                             "React composition patterns that scale for component libraries.")
        self.assertNotIn("deploy", tags)
        self.assertIn("frontend", tags)

    def test_single_description_word_does_not_tag(self):
        tags = MOD.tag_skill("threat-model", "Enumerates abuse paths; writes a design note.")
        self.assertNotIn("design", tags)

    def test_name_hit_tags(self):
        self.assertIn("deploy", MOD.tag_skill("vercel:deployments-cicd", "Ship things."))

    def test_untagged_is_general(self):
        self.assertEqual(MOD.tag_skill("zzz", "nothing relevant"), ["general"])


class ParseSkillTests(unittest.TestCase):
    def test_folded_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "demo-skill"
            d.mkdir()
            (d / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: >-\n  Helps with frontend ui\n  and react polish.\n"
                "license: MIT\n---\n\n# Demo\n")
            parsed = MOD.parse_skill(d / "SKILL.md", "claude")
            self.assertEqual(parsed["name"], "demo-skill")
            self.assertEqual(parsed["desc"], "Helps with frontend ui and react polish.")
            self.assertIn("frontend", parsed["tags"])
            self.assertEqual(parsed["found_in"], ["claude"])

    def test_quoted_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_skill(Path(tmp), "q", "q", '"Quoted: with colon"')
            self.assertEqual(MOD.parse_skill(p)["desc"], "Quoted: with colon")

    def test_no_frontmatter_uses_dirname(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "bare"
            d.mkdir()
            (d / "SKILL.md").write_text("# just markdown\n")
            self.assertEqual(MOD.parse_skill(d / "SKILL.md")["name"], "bare")

    def test_plugin_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_skill(Path(tmp), "deploy", "deploy", "Deploy to prod")
            self.assertEqual(MOD.parse_skill(p, "plugin:vercel", prefix="vercel")["name"], "vercel:deploy")

    def test_skips_system(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = write_skill(Path(tmp) / ".system", "x", "x", "test")
            self.assertIsNone(MOD.parse_skill(p))


class CollectTests(FakeHome):
    def test_skips_backups_and_hidden_dirs(self):
        root = self.home / ".claude" / "skills"
        write_skill(root, "real", "real", "A real skill")
        write_skill(root, "nummode.bak.20261011113635", "nummode", "old copy")
        write_skill(root, ".hidden", "hidden", "nope")
        names = [r["name"] for r in MOD.collect_skills()[0]]
        self.assertEqual(names, ["real"])

    def test_same_skill_in_two_roots_merges_found_in(self):
        write_skill(self.home / ".agents" / "skills", "s", "s", "same")
        write_skill(self.home / ".claude" / "skills", "s", "s", "same")
        rows, collisions = MOD.collect_skills()
        self.assertEqual(rows[0]["found_in"], ["agents", "claude"])
        self.assertEqual(collisions, [])

    def test_collision_reported_when_content_differs(self):
        write_skill(self.home / ".agents" / "skills", "s", "s", "one")
        write_skill(self.home / ".claude" / "skills", "s", "s", "two")
        rows, collisions = MOD.collect_skills()
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(collisions), 1)

    def test_enabled_plugins_indexed_disabled_skipped(self):
        plugins = self.home / ".claude" / "plugins"
        on = plugins / "cache" / "mkt" / "vercel" / "1.0"
        off = plugins / "cache" / "mkt" / "stripe" / "1.0"
        write_skill(on / "skills", "deploy", "deploy", "Deploy apps")
        write_skill(off / "skills", "pay", "pay", "Pay")
        (plugins / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": {
            "vercel@mkt": [{"installPath": str(on)}],
            "stripe@mkt": [{"installPath": str(off)}],
        }}))
        (self.home / ".claude" / "settings.json").write_text(json.dumps(
            {"enabledPlugins": {"vercel@mkt": True, "stripe@mkt": False}}))
        rows, _ = MOD.collect_skills()
        self.assertEqual([(r["name"], r["found_in"]) for r in rows], [("vercel:deploy", ["plugin:vercel"])])

    def test_broken_plugin_manifest_is_ignored(self):
        plugins = self.home / ".claude" / "plugins"
        plugins.mkdir(parents=True)
        (plugins / "installed_plugins.json").write_text("{not json")
        self.assertEqual(MOD.collect_skills()[0], [])


class SyncedTests(FakeHome):
    def bucket(self, name, stamp, skills):
        b = self.home / ".claude" / "skills" / "synced" / name
        for sk_name in skills:
            write_skill(b, sk_name, sk_name, f"{sk_name} from {name}")
        (b / "manifest.json").write_text(json.dumps({"lastUpdated": stamp, "skills": []}))

    def test_newest_synced_bucket_is_indexed_with_prefix(self):
        self.bucket("old-account", 1000, ["deep-research", "pdf"])
        self.bucket("new-account", 2000, ["skill-creator", "pdf"])
        (self.home / ".claude" / "skills" / "synced" / ".bucket-x").mkdir()
        rows, _ = MOD.collect_skills()
        self.assertEqual([(r["name"], r["found_in"]) for r in rows],
                         [("anthropic-skills:pdf", ["synced"]), ("anthropic-skills:skill-creator", ["synced"])])

    def test_broken_manifest_falls_back_to_mtime(self):
        b = self.home / ".claude" / "skills" / "synced" / "only"
        write_skill(b, "docx", "docx", "Word files")
        (b / "manifest.json").write_text("{nope")
        self.assertEqual([r["name"] for r in MOD.collect_skills()[0]], ["anthropic-skills:docx"])


class FreshnessTests(FakeHome):
    def test_check_cycle(self):
        root = self.home / ".claude" / "skills"
        write_skill(root, "a", "a", "first")
        self.assertEqual(MOD.main(["--check"]), 3)          # missing
        self.assertEqual(MOD.main(["--quiet"]), 0)
        self.assertEqual(MOD.main(["--check"]), 0)          # fresh
        write_skill(root, "b", "b", "second")
        self.assertEqual(MOD.main(["--check"]), 3)          # skills changed
        data = json.loads((self.home / ".nummode" / "skill-index.json").read_text())
        self.assertEqual(data["schema"], MOD.INDEX_SCHEMA)
        md = (self.home / ".nummode" / "skill-index.md").read_text()
        self.assertIn("`a`", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
