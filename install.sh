#!/usr/bin/env bash
# Install nummode into Claude Code (~/.claude)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
AGENTS_DIR="${CLAUDE_DIR}/agents"
NUMMODE_DIR="${CLAUDE_DIR}/nummode"

mkdir -p "${AGENTS_DIR}" "${NUMMODE_DIR}/playbooks" "${NUMMODE_DIR}/scripts"

cp "${ROOT}/agents/nummode.md" "${AGENTS_DIR}/nummode.md"
cp -R "${ROOT}/nummode/playbooks/." "${NUMMODE_DIR}/playbooks/"
cp -R "${ROOT}/nummode/scripts/." "${NUMMODE_DIR}/scripts/"
chmod +x "${NUMMODE_DIR}/scripts/refresh-index.py" 2>/dev/null || true

if [[ -d "${CLAUDE_DIR}/skills" ]]; then
  python3 "${NUMMODE_DIR}/scripts/refresh-index.py"
else
  mkdir -p "${CLAUDE_DIR}/skills"
  cp "${ROOT}/nummode/skill-index.md" "${NUMMODE_DIR}/skill-index.md"
  echo "No skills found at ~/.claude/skills — placeholder index installed."
  echo "Install skills, then run: python3 ~/.claude/nummode/scripts/refresh-index.py"
fi

SETTINGS="${CLAUDE_DIR}/settings.json"
if [[ -f "${SETTINGS}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / ".claude" / "settings.json"
data = json.loads(p.read_text())
if data.get("agent") != "nummode":
    data["agent"] = "nummode"
    p.write_text(json.dumps(data, indent=2) + "\n")
    print("Set default agent to nummode in ~/.claude/settings.json")
else:
    print("Default agent already nummode")
PY
  else
    echo "Install complete. To make nummode default, set \"agent\": \"nummode\" in ${SETTINGS}"
  fi
else
  printf '{\n  "agent": "nummode"\n}\n' > "${SETTINGS}"
  echo "Created ${SETTINGS} with agent=nummode"
fi

echo
echo "nummode installed."
echo "  Agent:  ${AGENTS_DIR}/nummode.md"
echo "  Data:   ${NUMMODE_DIR}"
echo "  Start:  claude --agent nummode"
echo "  Or open a new Claude Code session (default agent is nummode)."
