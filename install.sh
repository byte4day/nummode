#!/usr/bin/env bash
# Install nummode for Claude Code, Cursor, and Codex
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
NUMMODE_HOME="${HOME}/.nummode"

TARGETS="all" # all | claude | cursor | codex
SET_DEFAULT_AGENT=0
for arg in "$@"; do
  case "${arg}" in
    --set-default) SET_DEFAULT_AGENT=1 ;;
    --*)
      echo "Unknown flag: ${arg}"
      echo "Usage: ./install.sh [all|claude|cursor|codex] [--set-default]"
      exit 1
      ;;
    all|claude|cursor|codex) TARGETS="${arg}" ;;
    *)
      echo "Usage: ./install.sh [all|claude|cursor|codex] [--set-default]"
      exit 1
      ;;
  esac
done

install_shared() {
  mkdir -p "${NUMMODE_HOME}/playbooks" "${NUMMODE_HOME}/scripts"
  cp -R "${ROOT}/nummode/playbooks/." "${NUMMODE_HOME}/playbooks/"
  cp -R "${ROOT}/nummode/scripts/." "${NUMMODE_HOME}/scripts/"
  chmod +x "${NUMMODE_HOME}/scripts/refresh-index.py" 2>/dev/null || true

  # Universal skill (skills.sh / ~/.agents) — keep indexer identical to ~/.nummode
  mkdir -p "${HOME}/.agents/skills/nummode/references" "${HOME}/.agents/skills/nummode/scripts"
  cp "${ROOT}/skills/nummode/SKILL.md" "${HOME}/.agents/skills/nummode/SKILL.md"
  cp -R "${ROOT}/skills/nummode/references/." "${HOME}/.agents/skills/nummode/references/"
  cp "${NUMMODE_HOME}/scripts/refresh-index.py" "${HOME}/.agents/skills/nummode/scripts/refresh-index.py"
  chmod +x "${HOME}/.agents/skills/nummode/scripts/refresh-index.py" 2>/dev/null || true

  python3 "${NUMMODE_HOME}/scripts/refresh-index.py" || {
    cp "${ROOT}/nummode/skill-index.md" "${NUMMODE_HOME}/skill-index.md"
    echo "Skill index placeholder installed (refresh later)."
  }
}

link_skill() {
  local dest_root="$1"
  mkdir -p "${dest_root}"
  local dest="${dest_root}/nummode"
  if [[ -e "${dest}" && ! -L "${dest}" ]]; then
    echo "  warning: ${dest} exists and is not a symlink; leaving it alone"
    return 0
  fi
  ln -sfn "${HOME}/.agents/skills/nummode" "${dest}"
  echo "  skill → ${dest}"
}

install_claude() {
  echo "Installing Claude Code…"
  mkdir -p "${HOME}/.claude/agents" "${HOME}/.claude/skills"
  cp "${ROOT}/agents/claude/nummode.md" "${HOME}/.claude/agents/nummode.md"
  link_skill "${HOME}/.claude/skills"

  # Compat symlink for older paths
  if [[ -e "${HOME}/.claude/nummode" && ! -L "${HOME}/.claude/nummode" ]]; then
    echo "  warning: ~/.claude/nummode exists and is not a symlink; leaving it alone"
  else
    ln -sfn "${NUMMODE_HOME}" "${HOME}/.claude/nummode"
  fi

  local settings="${HOME}/.claude/settings.json"
  if [[ -f "${settings}" ]]; then
    SET_DEFAULT_AGENT="${SET_DEFAULT_AGENT}" python3 - <<'PY'
import json
import os
from pathlib import Path
p = Path.home() / ".claude" / "settings.json"
data = json.loads(p.read_text())
force = os.environ.get("SET_DEFAULT_AGENT") == "1"
current = data.get("agent")
if force or not current:
    data["agent"] = "nummode"
    p.write_text(json.dumps(data, indent=2) + "\n")
    print("  default agent → nummode")
else:
    print(f"  keeping existing agent={current} (pass --set-default to override)")
PY
  else
    printf '{\n  "agent": "nummode"\n}\n' > "${settings}"
    echo "  created settings with agent=nummode"
  fi
  echo "  agent → ~/.claude/agents/nummode.md"
}

install_cursor() {
  echo "Installing Cursor…"
  mkdir -p "${HOME}/.cursor/agents" "${HOME}/.cursor/skills"
  cp "${ROOT}/agents/cursor/nummode.md" "${HOME}/.cursor/agents/nummode.md"
  link_skill "${HOME}/.cursor/skills"
  echo "  agent → ~/.cursor/agents/nummode.md"
}

install_codex() {
  echo "Installing Codex…"
  mkdir -p "${HOME}/.codex/agents" "${HOME}/.codex/skills"
  cp "${ROOT}/agents/codex/nummode.toml" "${HOME}/.codex/agents/nummode.toml"
  link_skill "${HOME}/.codex/skills"

  python3 - <<'PY'
import re
from pathlib import Path
cfg = Path.home() / ".codex" / "config.toml"
cfg.parent.mkdir(parents=True, exist_ok=True)
text = cfg.read_text() if cfg.exists() else ""
if re.search(r"(?m)^\s*multi_agent\s*=\s*true\s*$", text):
    print("  multi_agent already enabled in config.toml")
elif re.search(r"(?m)^\s*multi_agent\s*=\s*false\s*$", text):
    cfg.write_text(re.sub(r"(?m)^(\s*multi_agent\s*=\s*)false\s*$", r"\1true", text))
    print("  set multi_agent = true")
elif not text.strip():
    cfg.write_text('personality = "pragmatic"\n\n[features]\nmulti_agent = true\n')
    print("  created ~/.codex/config.toml with multi_agent")
elif "[features]" in text:
    lines = text.splitlines(keepends=True)
    out = []
    inserted = False
    for line in lines:
        out.append(line)
        if not inserted and line.strip() == "[features]":
            out.append("multi_agent = true\n")
            inserted = True
    if not inserted:
        out.append("\n[features]\nmulti_agent = true\n")
    cfg.write_text("".join(out))
    print("  enabled multi_agent in existing [features]")
else:
    cfg.write_text(text.rstrip() + "\n\n[features]\nmulti_agent = true\n")
    print("  added [features] multi_agent = true")
PY
  echo "  agent → ~/.codex/agents/nummode.toml"
}

install_shared

case "${TARGETS}" in
  all)
    install_claude
    install_cursor
    install_codex
    ;;
  claude) install_claude ;;
  cursor) install_cursor ;;
  codex) install_codex ;;
esac

echo
echo "nummode ready (${TARGETS})."
echo "  Shared:  ~/.nummode/"
echo "  Skill:   ~/.agents/skills/nummode"
echo "  Claude:  claude --agent nummode"
echo "  Cursor:  use @nummode or the nummode skill on a big prompt"
echo "  Codex:   spawn/select agent_type nummode (or start with the nummode role)"
echo
echo "Also: npx skills add byte4day/nummode -g -y -a cursor -a codex -a claude-code"
echo "      (skills CLI alone is not enough — always run ./install.sh for playbooks + agents)"
