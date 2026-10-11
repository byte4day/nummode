#!/usr/bin/env bash
# Pull latest nummode and reinstall into the current harnesses.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "${ROOT}"

if [[ -d .git ]]; then
  echo "Updating nummode from git…"
  git pull --ff-only
else
  echo "Not a git checkout — reinstalling from local tree only."
fi

chmod +x "${ROOT}/install.sh"
exec "${ROOT}/install.sh" "$@"
