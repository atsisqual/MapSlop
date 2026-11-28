#!/usr/bin/env bash
# Stage an isolated viewer in a local output directory. Only fetch software, not map data.
set -euo pipefail
out="$(realpath "$1")"
test -f "$out/church-report.json" && test -f "$out/tileset.json" && test -f "$out/church.glb"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
git init -q "$work/three"
git -C "$work/three" remote add origin https://github.com/mrdoob/three.js.git
git -C "$work/three" sparse-checkout set build examples/jsm
git -C "$work/three" fetch --depth=1 --filter=blob:none origin f17eb5d689094a3fbd4cd0d64d54729a48036ce0
git -C "$work/three" checkout -q --detach FETCH_HEAD
mkdir -p "$out/vendor/three"
cp -r "$work/three/build" "$work/three/examples" "$work/three/LICENSE" "$out/vendor/three/"
mkdir "$work/npm"
cd "$work/npm"
npm init -y >/dev/null
npm install --save-exact --no-audit --no-fund --legacy-peer-deps 3d-tiles-renderer@0.5.4 esbuild@0.25.12
cd -
cp tools/local-3d/viewer.js "$work/npm/viewer.js"
"$work/npm/node_modules/.bin/esbuild" "$work/npm/viewer.js" --bundle --format=esm --platform=browser --external:three --external:three/* --outfile="$out/viewer.js"
cp tools/local-3d/index.html "$out/index.html"
cp "$work/npm/package-lock.json" "$out/toolchain-lock.json"
cp "$work/npm/node_modules/3d-tiles-renderer/LICENSE" "$out/3D-TILES-LICENSE.txt"
