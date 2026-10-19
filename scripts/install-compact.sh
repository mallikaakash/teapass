#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version=0.31.1
case "$(uname -s)-$(uname -m)" in
  Darwin-arm64) target=aarch64-darwin; expected=57af9b0449aa96b2905ea3d7a175b6b42ab38d725612a9cb2d73eb4ef253cce2 ;;
  Darwin-x86_64) target=x86_64-darwin; expected=eebae2d04b1ec05fe07d06398e36d78e60cf4927ddbc0dae7d5f5ebb9ac6721c ;;
  Linux-aarch64) target=aarch64-unknown-linux-musl; expected=7c7e38581808779d2671687c3378017bcf2fb3111a192fd1253f3472012df549 ;;
  Linux-x86_64) target=x86_64-unknown-linux-musl; expected=e291b4bab4d4e857707008f8b1c25c2b8e0c843f6c737d0ee6c0d9ac69a6bbfb ;;
  *) echo "Unsupported platform" >&2; exit 1 ;;
esac
destination="$project_root/.tools/compact/$version"
if [[ -x "$destination/compactc" ]] && [[ "$("$destination/compactc" --version)" == "$version" ]]; then
  echo "Compact compiler $version already installed in the project"
  exit 0
fi
temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT
curl --proto '=https' --tlsv1.2 --fail --location --connect-timeout 20 --max-time 180 \
  "https://github.com/midnightntwrk/compact/releases/download/compactc-v$version/compactc_v${version}_${target}.zip" \
  -o "$temporary_dir/compiler.zip"
actual="$(shasum -a 256 "$temporary_dir/compiler.zip" | cut -d ' ' -f 1)"
[[ "$actual" == "$expected" ]] || { echo "Compiler checksum mismatch" >&2; exit 1; }
mkdir -p "$destination"
unzip -q "$temporary_dir/compiler.zip" -d "$destination"
"$destination/compactc" --version
