#!/usr/bin/env python3
"""Tests for relay.py using fake harness binaries (no network, no real agents)."""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "nummode" / "scripts" / "relay.py"
spec = importlib.util.spec_from_file_location("relay", SCRIPT)
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

FAKE = """#!/usr/bin/env python3
import os, sys, time
args = sys.argv[1:]
prompt = sys.stdin.read() if not sys.stdin.isatty() else ""
if os.environ.get("FAKE_SLEEP"):
    time.sleep(float(os.environ["FAKE_SLEEP"]))
if os.environ.get("FAKE_FAIL"):
    print("boom", file=sys.stderr); sys.exit(3)
print("FAKE RESULT")
print("depth=" + os.environ.get("NUMMODE_RELAY_DEPTH", "?"))
print("args=" + " ".join(args))
print("prompt_has_task=" + str("TASK-MARKER" in (prompt + " ".join(args))))
"""


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        fake = self.dir / "fake-agent"
        fake.write_text(FAKE)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.env = os.environ.copy()
        for h in R.HARNESSES:
            self.env[f"NUMMODE_RELAY_{h.upper()}_BIN"] = str(fake)
        for k in ("NUMMODE_RELAY_DEPTH", "NUMMODE_RELAY_DIR", "NUMMODE_RELAY_MAX_DEPTH"):
            self.env.pop(k, None)

    def tearDown(self):
        self.tmp.cleanup()

    def run_relay(self, *args, env=None, check=True):
        p = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.dir, env=env or self.env,
                           capture_output=True, text=True, timeout=60)
        if check and p.returncode != 0:
            self.fail(f"relay {args} exited {p.returncode}: {p.stderr}{p.stdout}")
        return p

    def only_task(self):
        tasks = [d for d in (self.dir / ".relay").iterdir() if d.is_dir()]
        self.assertEqual(len(tasks), 1)
        return tasks[0]

    def test_wait_mode_writes_result_and_meta(self):
        p = self.run_relay("dispatch", "--to", "claude", "--task", "do TASK-MARKER", "--wait")
        self.assertIn("FAKE RESULT", p.stdout)
        task = self.only_task()
        result = (task / "result.md").read_text()
        self.assertIn("prompt_has_task=True", result)
        self.assertIn("depth=1", result)
        meta = json.loads((task / "meta.json").read_text())
        self.assertEqual((meta["status"], meta["exit_code"], meta["mode"]), ("done", 0, "read"))
        self.assertEqual((task / "brief.md").read_text().strip(), "do TASK-MARKER")
        self.assertEqual((self.dir / ".relay" / ".gitignore").read_text().splitlines()[-1], "*")

    def test_background_dispatch_then_wait_and_result(self):
        env = self.env | {"FAKE_SLEEP": "0.5"}
        p = self.run_relay("dispatch", "--to", "cursor", "--task", "TASK-MARKER", "--name", "bg", "--json", env=env)
        meta = json.loads(p.stdout)
        self.assertEqual(meta["status"], "starting")
        self.assertIn("-bg-", meta["id"])
        w = self.run_relay("wait", "--timeout", "30", "--poll", "0.1")
        self.assertIn("done", w.stdout)
        r = self.run_relay("result", meta["id"][:20])
        self.assertIn("FAKE RESULT", r.stdout)
        self.assertIn("--mode ask", r.stdout)  # cursor read mode

    def test_failure_recorded(self):
        env = self.env | {"FAKE_FAIL": "1"}
        p = self.run_relay("dispatch", "--to", "opencode", "--task", "x", "--wait", env=env, check=False)
        self.assertEqual(p.returncode, 1)
        meta = json.loads((self.only_task() / "meta.json").read_text())
        self.assertEqual((meta["status"], meta["exit_code"]), ("failed", 3))
        self.assertIn("boom", (self.only_task() / "log.txt").read_text())

    def test_timeout(self):
        env = self.env | {"FAKE_SLEEP": "5"}
        p = self.run_relay("dispatch", "--to", "claude", "--task", "x", "--wait", "--timeout", "1", env=env, check=False)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads((self.only_task() / "meta.json").read_text())["status"], "timeout")

    def test_workers_cannot_start_workers(self):
        env = self.env | {"NUMMODE_RELAY_DEPTH": "1"}
        p = self.run_relay("dispatch", "--to", "codex", "--task", "x", env=env, check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("depth", p.stderr)

    def test_missing_harness(self):
        env = self.env | {"NUMMODE_RELAY_GEMINI_BIN": str(self.dir / "nope")}
        p = self.run_relay("dispatch", "--to", "gemini", "--task", "x", env=env, check=False)
        self.assertEqual(p.returncode, 4)

    def test_unknown_harness_and_aliases(self):
        self.assertEqual(R._canon("Claude-Code"), "claude")
        self.assertEqual(R._canon("agy"), "antigravity")
        with self.assertRaises(SystemExit):
            R._canon("notepad")

    def test_dry_run_and_harnesses_json(self):
        self.run_relay("dispatch", "--to", "codex", "--task", "x", "--dry-run")
        self.assertEqual(json.loads((self.only_task() / "meta.json").read_text())["status"], "dry-run")
        rows = json.loads(self.run_relay("harnesses", "--json").stdout)["harnesses"]
        self.assertEqual({r["name"] for r in rows}, set(R.HARNESSES))
        self.assertTrue(all(r["available"] for r in rows))


class CommandTemplateTests(unittest.TestCase):
    def build(self, harness, mode):
        return R.build_command(harness, "/bin/x", "PROMPT", mode, Path("/w"), Path("/w/r.md"), model="m1")

    def test_read_mode_is_restricted_everywhere(self):
        cmd, stdin = self.build("claude", "read")
        self.assertIn("--disallowedTools", cmd)
        self.assertNotIn("--dangerously-skip-permissions", cmd)
        self.assertEqual(stdin, "PROMPT")
        cmd, _ = self.build("codex", "read")
        self.assertEqual(cmd[cmd.index("-s") + 1], "read-only")
        self.assertEqual(cmd[cmd.index("-o") + 1], "/w/r.md")
        cmd, stdin = self.build("cursor", "read")
        self.assertIn("ask", cmd)
        self.assertNotIn("--force", cmd)
        self.assertIsNone(stdin)
        cmd, _ = self.build("gemini", "read")
        self.assertEqual(cmd[cmd.index("--approval-mode") + 1], "default")
        cmd, _ = self.build("opencode", "read")
        self.assertNotIn("--auto", cmd)

    def test_write_and_full_modes(self):
        self.assertIn("acceptEdits", self.build("claude", "write")[0])
        self.assertIn("--dangerously-skip-permissions", self.build("claude", "full")[0])
        self.assertIn("workspace-write", self.build("codex", "write")[0])
        self.assertIn("--dangerously-bypass-approvals-and-sandbox", self.build("codex", "full")[0])
        self.assertIn("--force", self.build("cursor", "write")[0])
        self.assertIn("--auto", self.build("opencode", "write")[0])

    def test_prompt_contract(self):
        p = R.compose_prompt("Find X", Path("/r/t"), "read", "claude", [Path("/a.md")])
        for needle in ("Find X", "FINAL message", "Read-only", "/a.md", "Do not start other agents"):
            self.assertIn(needle, p)
        w = R.compose_prompt("Fix Y", Path("/r/t"), "write", None, [])
        self.assertIn("Changed files", w)
        self.assertIn("/r/t/files", w)


if __name__ == "__main__":
    unittest.main(verbosity=1)
