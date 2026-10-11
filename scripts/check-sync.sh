#!/usr/bin/env bash
# Fail if duplicated canonical files drift apart.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0

check() {
  local a="$1" b="$2"
  if ! diff -q "${ROOT}/${a}" "${ROOT}/${b}" >/dev/null; then
    echo "DRIFT: ${a} ≠ ${b}" >&2
    diff -u "${ROOT}/${a}" "${ROOT}/${b}" >&2 || true
    fail=1
  else
    echo "ok  ${a}"
  fi
}

check nummode/scripts/refresh-index.py skills/nummode/scripts/refresh-index.py
check nummode/scripts/route.py skills/nummode/scripts/route.py
check nummode/playbooks/missions.md skills/nummode/references/missions.md
check nummode/playbooks/intake.md skills/nummode/references/intake.md

exit "${fail}"
