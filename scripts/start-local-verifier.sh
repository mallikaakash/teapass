#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
# Public address only. Ephemeral genesis seeds are never read or printed here.
TEAPASS_MIDNIGHT_CONTRACT_ADDRESS="$(python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p["complete"] and p["networkId"]=="undeployed"; print(p["contractAddress"])' "$root/artifacts/midnight/inventory-local.json")"
export TEAPASS_MIDNIGHT_CONTRACT_ADDRESS
cd "$root/packages/compact-contracts"
exec npm run verifier
