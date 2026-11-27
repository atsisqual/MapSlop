#!/usr/bin/env python3
"""Offline checks for handoff docs, immutable evidence and workflow triggers."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote
import yaml

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
paths = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\x00")
paths = [Path(p) for p in paths if p]
errors = []
links = 0
for p in paths:
    if p.is_symlink():
        continue
    if p.stat().st_size > 50_000_000:
        errors.append(f"Large tracked file: {p}")
    if p.suffix.lower() in {".har", ".tif", ".tiff", ".laz", ".las", ".pbf"}:
        errors.append(f"Raw data or HAR tracked: {p}")
    if p.suffix != ".md":
        continue
    s = p.read_text(encoding="utf-8")
    if len(re.findall(r"(?m)^\s*" + chr(96)*3, s)) % 2:
        errors.append(f"Unbalanced Markdown fences: {p}")
    for link in re.findall(r"\]\(([^)\n]+)\)", s):
        if re.match(r"^(https?:|mailto:|#)", link):
            continue
        target = unquote(link.split("#", 1)[0].strip().strip("<>"))
        if target and not (p.parent / target).exists():
            errors.append(f"Broken internal link: {p} -> {link}")
        links += 1

if not Path("CLAUDE.md").is_symlink() or os.readlink("CLAUDE.md") != "AGENTS.md":
    errors.append("CLAUDE.md must be a symlink to AGENTS.md")

wf = Path(".github/workflows")
workflows = {}
for p in wf.glob("*.yml"):
    content = yaml.load(p.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    workflows[p.name] = content
manual = {"archive-portugal.yml", "dgt.yml", "expanded-vectors.yml", "pedome-terrain.yml", "reconstruction-archive.yml", "pedome-dgt-terrain.yml"}
for name in manual:
    allowed = {"workflow_dispatch", "workflow_call"} if name == "pedome-dgt-terrain.yml" else {"workflow_dispatch"}
    if set(workflows[name]["on"]) != allowed:
        errors.append(f"Data workflow not manual: {name}")
for name, workflow in workflows.items():
    for job in workflow.get("jobs", {}).values():
        if job.get("uses") == "./.github/workflows/pedome-dgt-terrain.yml":
            if name != "pedome-terrain.yml" or set(workflow["on"]) != {"workflow_dispatch"}:
                errors.append("DGT terrain must be called only by the registered manual launcher")
if "pedome-dgt-buildings.yml" in workflows:
    if set(workflows["pedome-dgt-buildings.yml"]["on"]) != {"workflow_call"}:
        errors.append("Building data workflow must be callable only")
    for name, workflow in workflows.items():
        for job in workflow.get("jobs", {}).values():
            if job.get("uses") == "./.github/workflows/pedome-dgt-buildings.yml":
                if name != "pedome-terrain.yml" or set(workflow["on"]) != {"workflow_dispatch"}:
                    errors.append("DGT buildings must be called only by the registered manual launcher")
if "pedome-dgt-roofs.yml" in workflows:
    if set(workflows["pedome-dgt-roofs.yml"]["on"]) != {"workflow_call"}:
        errors.append("Roof data workflow must be callable only")
    for name, workflow in workflows.items():
        for job in workflow.get("jobs", {}).values():
            if job.get("uses") == "./.github/workflows/pedome-dgt-roofs.yml":
                if name != "pedome-terrain.yml" or set(workflow["on"]) != {"workflow_dispatch"}:
                    errors.append("DGT roofs must be called only by the manual launcher")
if "pedome-dgt-roads.yml" in workflows:
    if set(workflows["pedome-dgt-roads.yml"]["on"]) != {"workflow_call"}:
        errors.append("Road data workflow must be callable only")
    for name, workflow in workflows.items():
        for job in workflow.get("jobs", {}).values():
            if job.get("uses") == "./.github/workflows/pedome-dgt-roads.yml":
                if name != "pedome-terrain.yml" or set(workflow["on"]) != {"workflow_dispatch"}:
                    errors.append("DGT roads must be called only by the manual launcher")
if any(n.startswith("dgt-") for n in workflows):
    errors.append("Duplicated DGT workflows")
if workflows["pages.yml"]["on"]["push"]["branches"] != ["main"]:
    errors.append("Pages push must target main")
if "pull_request" not in workflows["ci.yml"]["on"] or workflows["ci.yml"]["permissions"].get("contents") != "read":
    errors.append("PR CI must be read-only")

catalog = Path("docs/data-catalog.md").read_text()
for p in ("data/pedome/pedome-osm.json", "data/pedome/caop2025-pedome.geojson",
          "data/pedome/cos2025-pilot.geojson", "data/pedome/dgt-items.json"):
    with Path(p).open("rb") as f:
        sha = hashlib.file_digest(f, "sha256").hexdigest()
    if not re.search(re.escape(p) + r"\]\(\.\./" + re.escape(p) + r"\).*?" + sha, catalog):
        errors.append(f"Data catalogue hash mismatch: {p}")
inv = json.loads(Path("docs/research/release-assets-20261127.json").read_text())
for r in inv["releases"]:
    assets = r["assets"]
    if r["asset_count"] != len(assets) or r["total_bytes"] != sum(a["bytes"] for a in assets):
        errors.append("Invalid release totals: " + r["tag"])
    if not all(re.fullmatch(r"[0-9a-f]{64}", a["sha256"]) for a in assets):
        errors.append("Invalid release SHA-256: " + r["tag"])
    if len({a["name"] for a in assets}) != len(assets):
        errors.append("Duplicate asset names: " + r["tag"])
    if r["draft"] is not True:
        errors.append("Historical evidence must keep original draft state")
if errors:
    raise SystemExit("\n".join(errors))
print(f"Repository checks OK: {links} internal links, {len(workflows)} parsed workflows, {sum(len(r['assets']) for r in inv['releases'])} archived asset digests, 4 small dataset hashes.")
