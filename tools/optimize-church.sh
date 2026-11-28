#!/usr/bin/env bash
set -euo pipefail
out="$(realpath "$1")"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cp tools/optimize-church.mjs "$work/"
(
cd "$work"
npm init -y >/dev/null
npm install --save-exact --no-audit --no-fund @gltf-transform/core@4.1.1 @gltf-transform/extensions@4.1.1 @gltf-transform/functions@4.1.1 sharp@0.34.5
cp package-lock.json "$out/optimization-toolchain-lock.json"
node optimize-church.mjs "$out"
)
