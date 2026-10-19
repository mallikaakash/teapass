#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
"$root/scripts/install-compact.sh"
"$root/scripts/midnight-devnet.sh" up -d --wait --wait-timeout 180
cd "$root/packages/compact-contracts"
npm ci --ignore-scripts
npm run compile:all
npm run typecheck
npm test
npm run test:local
npm run test:inventory:local
npx --no-install vite-node src/verify-local-evidence.ts
