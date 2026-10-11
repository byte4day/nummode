#!/usr/bin/env bash
# Remove nummode agents, skill links and shipped files.
# Keeps user-added playbooks and ~/.nummode/backups unless --purge is passed.
# Never edits Codex features.multi_agent.
set -euo pipefail

PURGE=0
for arg in "$@"; do
  case "${arg}" in
    --purge) PURGE=1 ;;
    *) echo "Usage: ./uninstall.sh [--purge]" >&2; exit 1 ;;
  esac
done

NUMMODE_HOME="${HOME}/.nummode"
echo "Removing nummode…"

rm -f "${HOME}/.claude/agents/nummode.md" "${HOME}/.cursor/agents/nummode.md" "${HOME}/.codex/agents/nummode.toml"

# Harness links: remove only symlinks (a real directory there is not ours to delete).
for link in "${HOME}/.claude/skills/nummode" "${HOME}/.cursor/skills/nummode" "${HOME}/.codex/skills/nummode" "${HOME}/.claude/nummode"; do
  if [[ -L "${link}" ]]; then
    rm "${link}"
  elif [[ -e "${link}" ]]; then
    echo "  kept ${link} (not a symlink; remove it by hand if it is an old nummode copy)"
  fi
done

rm -rf "${HOME}/.agents/skills/nummode"

if [[ "${PURGE}" -eq 1 ]]; then
  rm -rf "${NUMMODE_HOME}"
  echo "  purged ${NUMMODE_HOME}"
elif [[ -d "${NUMMODE_HOME}" ]]; then
  rm -f "${NUMMODE_HOME}/skill-index.md" "${NUMMODE_HOME}/skill-index.json" "${NUMMODE_HOME}/VERSION"
  rm -f "${NUMMODE_HOME}/playbooks/missions.md" "${NUMMODE_HOME}/playbooks/intake.md"
  rm -rf "${NUMMODE_HOME}/scripts"
  rmdir "${NUMMODE_HOME}/playbooks" 2>/dev/null || true
  rmdir "${NUMMODE_HOME}" 2>/dev/null || echo "  kept ${NUMMODE_HOME} (user playbooks/backups inside; --purge removes it)"
fi

if [[ -f "${HOME}/.claude/settings.json" ]]; then
  python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / ".claude" / "settings.json"
try:
    data = json.loads(p.read_text())
except Exception:
    raise SystemExit(0)
if isinstance(data, dict) and data.get("agent") == "nummode":
    del data["agent"]
    p.write_text(json.dumps(data, indent=2) + "\n")
    print("  cleared agent=nummode from ~/.claude/settings.json")
PY
fi

echo "nummode removed."
echo "Note: Codex features.multi_agent is left unchanged."
