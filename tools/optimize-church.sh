#!/usr/bin/env bash
set -euo pipefail
out="$(realpath "$1")"
prior=""
if [ "$#" -gt 1 ]; then prior="$(realpath "$2")"; fi
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cp tools/optimize-church.mjs "$work/"
(
cd "$work"
npm init -y >/dev/null
npm install --save-exact --no-audit --no-fund @gltf-transform/core@4.1.1 @gltf-transform/extensions@4.1.1 @gltf-transform/functions@4.1.1 sharp@0.34.5
cp package-lock.json "$out/optimization-toolchain-lock.json"
if [ -n "$prior" ]; then node optimize-church.mjs "$out" "$prior"; else node optimize-church.mjs "$out"; fi
)
