#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case "$(docker info --format '{{.Architecture}}')" in
  aarch64|arm64)
    export MIDNIGHT_INDEXER_IMAGE='midnightntwrk/indexer-standalone:4.3.5-arm64@sha256:786c5ef5e5befc7293b86c2ebde46a29f54d6eb2d2d74df82f41ec3547669ef8'
    ;;
  x86_64|amd64)
    export MIDNIGHT_INDEXER_IMAGE='midnightntwrk/indexer-standalone:4.3.5@sha256:a660227c39d20bc317c718968417847cc97efc6832803154ccf0272c10e75558'
    ;;
  *) echo 'Unsupported Docker architecture' >&2; exit 1 ;;
esac
exec docker compose --progress plain -f "$project_root/infra/midnight/compose.yml" "$@"
