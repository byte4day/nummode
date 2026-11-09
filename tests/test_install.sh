#!/usr/bin/env bash
# Installer smoke test in a throwaway $HOME. Never touches the real home dir.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAKE="$(mktemp -d)"
trap 'rm -rf "${FAKE}"' EXIT
export HOME="${FAKE}"
unset NUMMODE_HOME NUMMODE_EXTRA_ROOTS
pass=0
ok() { echo "ok  $*"; pass=$((pass + 1)); }
die() { echo "FAIL $*" >&2; exit 1; }

# Pre-existing state the installer must handle.
mkdir -p "${HOME}/.claude/skills/nummode.bak.20260101000000" "${HOME}/.cursor/skills" "${HOME}/.codex/skills" "${HOME}/.claude/skills/debugging"
echo "---" > "${HOME}/.claude/skills/nummode.bak.20260101000000/SKILL.md"
# Stale duplicate skill symlinks from older installs should be removed.
ln -sfn /tmp/not-a-real-skill "${HOME}/.cursor/skills/nummode"
ln -sfn /tmp/not-a-real-skill "${HOME}/.codex/skills/nummode"
printf -- '---\nname: debugging\ndescription: Debug failing tests and bugs.\n---\n' > "${HOME}/.claude/skills/debugging/SKILL.md"
printf '{\n  "agent": "other"\n}\n' > "${HOME}/.claude/settings.json"
mkdir -p "${HOME}/.nummode/playbooks" && echo "mine" > "${HOME}/.nummode/playbooks/custom.md"

bash "${ROOT}/install.sh" all >/dev/null 2>&1 || die "install.sh failed"

for f in .nummode/scripts/route.py .nummode/scripts/refresh-index.py .nummode/playbooks/missions.md \
         .nummode/skill-index.json .nummode/VERSION .agents/skills/nummode/SKILL.md \
         .agents/skills/nummode/scripts/route.py .agents/skills/nummode/references/missions.md \
         .agents/skills/nummode/references/models-and-harness.md \
         .agents/skills/nummode/agents/openai.yaml \
         .claude/agents/nummode.md .cursor/agents/nummode.md .codex/agents/nummode.toml; do
  [[ -f "${HOME}/${f}" ]] || die "missing ${f}"
done
ok "files installed"

for l in .claude/skills/nummode .claude/nummode; do
  [[ -L "${HOME}/${l}" ]] || die "${l} is not a symlink"
done
# Cursor and Codex read ~/.agents/skills; duplicate skill links must not remain.
[[ ! -e "${HOME}/.cursor/skills/nummode" ]] || die "duplicate ~/.cursor/skills/nummode still present"
[[ ! -e "${HOME}/.codex/skills/nummode" ]] || die "duplicate ~/.codex/skills/nummode still present"
ok "harness links are symlinks"

compgen -G "${HOME}/.claude/skills/nummode.bak.*" >/dev/null && die "old backup still in skill root"
compgen -G "${HOME}/.nummode/backups/*" >/dev/null || die "backups dir empty"
ok "old backups moved out of skill roots"

[[ -f "${HOME}/.nummode/playbooks/custom.md" ]] || die "user playbook deleted"
ok "user playbook kept"

grep -q '"agent": "other"' "${HOME}/.claude/settings.json" || die "existing default agent overwritten"
grep -q 'multi_agent = true' "${HOME}/.codex/config.toml" || die "codex multi_agent not enabled"
ok "settings respected"

[[ "$(cat "${HOME}/.nummode/VERSION")" == "$(tr -d '[:space:]' < "${ROOT}/VERSION")" ]] || die "VERSION mismatch"
ok "version stamped"

out="$(cd "${FAKE}" && python3 "${HOME}/.nummode/scripts/route.py" --harness any "the test is failing, fix it")"
[[ "${out}" == "nummode · fix · skills: debugging"* ]] || die "route output: ${out}"
ok "installed router works"

python3 "${HOME}/.nummode/scripts/refresh-index.py" --check >/dev/null || die "index stale right after install"
ok "index fresh"

bash "${ROOT}/install.sh" claude >/dev/null 2>&1 || die "re-install failed"
[[ -L "${HOME}/.claude/skills/nummode" ]] || die "re-install broke link"
ok "re-install is idempotent"

bash "${ROOT}/uninstall.sh" >/dev/null 2>&1 || die "uninstall failed"
[[ ! -e "${HOME}/.agents/skills/nummode" && ! -L "${HOME}/.claude/skills/nummode" && ! -e "${HOME}/.claude/agents/nummode.md" ]] || die "uninstall left files"
[[ -f "${HOME}/.nummode/playbooks/custom.md" ]] || die "uninstall deleted user playbook"
[[ ! -e "${HOME}/.nummode/scripts" ]] || die "uninstall left scripts"
ok "uninstall keeps user data"

bash "${ROOT}/uninstall.sh" --purge >/dev/null 2>&1 || die "purge failed"
[[ ! -e "${HOME}/.nummode" ]] || die "purge left ~/.nummode"
ok "purge"

echo "${pass} checks passed"
