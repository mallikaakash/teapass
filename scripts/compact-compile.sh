#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
compiler="$project_root/.tools/compact/0.31.1/compactc"
export XDG_CACHE_HOME="$project_root/.tools/cache"
if [[ ! -x "$compiler" ]]; then
  echo "Pinned compiler missing. Run scripts/install-compact.sh first." >&2
  exit 1
fi
if [[ "$("$compiler" --version)" != "0.31.1" ]]; then
  echo "Refusing compiler version mismatch" >&2
  exit 1
fi
exec "$compiler" "$@"
