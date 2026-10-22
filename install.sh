#!/usr/bin/env bash
# Install nummode for Claude Code, Cursor, and Codex (idempotent; safe to re-run)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
NUMMODE_HOME="${HOME}/.nummode"
VERSION="$(tr -d '[:space:]' < "${ROOT}/VERSION" 2>/dev/null || echo "dev")"
WARNINGS=0

TARGETS="all" # all | claude | cursor | codex
SET_DEFAULT_AGENT=0
FORCE_MULTI_AGENT=0
SEEN_TARGET=0

usage() {
  echo "Usage: ./install.sh [all|claude|cursor|codex] [--set-default] [--force-multi-agent]"
}

for arg in "$@"; do
  case "${arg}" in
    --set-default) SET_DEFAULT_AGENT=1 ;;
    --force-multi-agent) FORCE_MULTI_AGENT=1 ;;
    --*)
      echo "Unknown flag: ${arg}" >&2
      usage >&2
      exit 1
      ;;
    all|claude|cursor|codex)
      if [[ "${SEEN_TARGET}" -eq 1 ]]; then
        echo "Error: only one target allowed (got '${TARGETS}' and '${arg}')." >&2
        usage >&2
        exit 1
      fi
      TARGETS="${arg}"
      SEEN_TARGET=1
      ;;
    *)
      usage >&2
      exit 1
      ;;
  esac
done

warn() {
  echo "  warning: $*" >&2
  WARNINGS=$((WARNINGS + 1))
}

BACKUP_DIR="${NUMMODE_HOME}/backups"
STAMP="$(date +%Y%m%d%H%M%S)"

# Move a path out of the way into ~/.nummode/backups (never next to a skill root,
# where harnesses would load the backup as a second "nummode" skill).
backup_path() {
  local target="$1" label="$2"
  mkdir -p "${BACKUP_DIR}"
  local dest="${BACKUP_DIR}/${label}.${STAMP}"
  mv "${target}" "${dest}"
  warn "moved ${target} → ${dest}"
}

# Earlier installers left nummode.bak.* dirs inside skill roots. Move them out.
migrate_old_backups() {
  local root old
  for root in "${HOME}/.claude/skills" "${HOME}/.cursor/skills" "${HOME}/.codex/skills" "${HOME}/.agents/skills" "${HOME}/.claude"; do
    [[ -d "${root}" ]] || continue
    for old in "${root}"/nummode.bak.*; do
      [[ -e "${old}" ]] || continue
      mkdir -p "${BACKUP_DIR}"
      mv "${old}" "${BACKUP_DIR}/$(basename "$(dirname "${old}")")-$(basename "${old}")"
      echo "  moved old backup ${old} → ${BACKUP_DIR}/"
    done
  done
}

install_shared() {
  mkdir -p "${NUMMODE_HOME}/playbooks" "${NUMMODE_HOME}/scripts"
  migrate_old_backups

  # Shipped playbooks only; user-added playbooks in ~/.nummode/playbooks are kept.
  cp "${ROOT}/nummode/playbooks/"*.md "${NUMMODE_HOME}/playbooks/"
  cp "${ROOT}/nummode/scripts/refresh-index.py" "${ROOT}/nummode/scripts/route.py" "${ROOT}/nummode/scripts/relay.py" "${NUMMODE_HOME}/scripts/"
  rm -rf "${NUMMODE_HOME}/scripts/__pycache__"
  chmod +x "${NUMMODE_HOME}/scripts/"*.py || warn "chmod failed in ~/.nummode/scripts"

  local skill="${HOME}/.agents/skills/nummode"
  if [[ -L "${skill}" ]]; then
    rm "${skill}"
  fi
  mkdir -p "${skill}/references" "${skill}/scripts"
  cp "${ROOT}/skills/nummode/SKILL.md" "${skill}/SKILL.md"
  cp "${ROOT}/skills/nummode/references/"*.md "${skill}/references/"
  cp "${ROOT}/skills/nummode/scripts/"*.py "${skill}/scripts/"
  rm -rf "${skill}/scripts/__pycache__"
  chmod +x "${skill}/scripts/"*.py || warn "chmod failed in ${skill}/scripts"
  printf '%s\n' "${VERSION}" > "${skill}/VERSION"
  printf '%s\n' "${VERSION}" > "${NUMMODE_HOME}/VERSION"

}

# Runs last, after harness links exist, so the index matches what is on disk.
refresh_index() {
  local script="${NUMMODE_HOME}/scripts/refresh-index.py"
  if ! NUMMODE_HOME="${NUMMODE_HOME}" python3 "${script}"; then
    cp "${ROOT}/nummode/skill-index.md" "${NUMMODE_HOME}/skill-index.md"
    warn "skill index refresh failed; placeholder installed (run refresh-index.py later)"
  fi
}

link_skill() {
  local dest_root="$1"
  mkdir -p "${dest_root}"
  local dest="${dest_root}/nummode"
  local canonical="${HOME}/.agents/skills/nummode"

  if [[ -e "${dest}" && ! -L "${dest}" ]]; then
    local owner
    owner="$(basename "${dest_root%/skills}")"
    backup_path "${dest}" "${owner#.}-skill-nummode"
  fi
  ln -sfn "${canonical}" "${dest}"
  echo "  skill → ${dest}"
}

install_claude() {
  echo "Installing Claude Code…"
  mkdir -p "${HOME}/.claude/agents" "${HOME}/.claude/skills"
  cp "${ROOT}/agents/claude/nummode.md" "${HOME}/.claude/agents/nummode.md"
  link_skill "${HOME}/.claude/skills"

  if [[ -e "${HOME}/.claude/nummode" && ! -L "${HOME}/.claude/nummode" ]]; then
    backup_path "${HOME}/.claude/nummode" "claude-nummode"
  fi
  ln -sfn "${NUMMODE_HOME}" "${HOME}/.claude/nummode"

  local settings="${HOME}/.claude/settings.json"
  if [[ -f "${settings}" ]]; then
    SET_DEFAULT_AGENT="${SET_DEFAULT_AGENT}" python3 - <<'PY' || warn "could not update ~/.claude/settings.json (invalid JSON?)"
import json
import os
import sys
from pathlib import Path

p = Path.home() / ".claude" / "settings.json"
try:
    data = json.loads(p.read_text())
except Exception as e:
    print(f"  settings.json parse error: {e}", file=sys.stderr)
    sys.exit(1)
if not isinstance(data, dict):
    print("  settings.json is not an object; skipping agent default", file=sys.stderr)
    sys.exit(1)
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

  FORCE_MULTI_AGENT="${FORCE_MULTI_AGENT}" python3 - <<'PY'
import os
import re
from pathlib import Path

force = os.environ.get("FORCE_MULTI_AGENT") == "1"
cfg = Path.home() / ".codex" / "config.toml"
cfg.parent.mkdir(parents=True, exist_ok=True)
text = cfg.read_text() if cfg.exists() else ""

if re.search(r"(?m)^\s*multi_agent\s*=\s*true\s*$", text):
    print("  multi_agent already enabled in config.toml")
elif re.search(r"(?m)^\s*multi_agent\s*=\s*false\s*$", text):
    if force:
        cfg.write_text(re.sub(r"(?m)^(\s*multi_agent\s*=\s*)false\s*$", r"\1true", text))
        print("  set multi_agent = true (--force-multi-agent)")
    else:
        print("  leaving multi_agent = false (pass --force-multi-agent to override)")
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
refresh_index

echo
echo "nummode ${VERSION} ready (${TARGETS})."
echo "  Shared:  ~/.nummode/"
echo "  Skill:   ~/.agents/skills/nummode"
echo "  Claude:  claude --agent nummode"
echo "  Cursor:  use @nummode or the nummode skill on a big prompt"
echo "  Codex:   spawn/select agent_type nummode (or start with the nummode role)"
echo "  Route:   python3 ~/.nummode/scripts/route.py \"<brief>\""
echo "  Update:  ./update.sh"
if [[ "${WARNINGS}" -gt 0 ]]; then
  echo
  echo "WARNINGS: ${WARNINGS} (see messages above)." >&2
fi
