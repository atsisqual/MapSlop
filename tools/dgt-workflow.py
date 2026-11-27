#!/usr/bin/env python3
"""Manual DGT acquisition and append-only draft archive. No secrets in arguments or manifests."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

TOOLS = Path(__file__).resolve().parent
MODES = ("pilot-public", "pilot-authenticated", "expanded", "laz", "historical", "collection")
COLLECTIONS = ("MDT-50cm", "MDS-50cm", "MDT-2m", "MDS-2m", "LAZ", "ORTOS-2025")
TIFF = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")

def plan(mode, collection, snapshot, output):
    if mode not in MODES or collection not in COLLECTIONS:
        raise ValueError("Unknown mode or collection")
    if not re.fullmatch(r"\d{8}", snapshot):
        raise ValueError("Snapshot must be YYYYMMDD")
    datetime.datetime.strptime(snapshot, "%Y%m%d")
    output = str(Path(output))
    if mode.startswith("pilot-"):
        cmd = [sys.executable, "-u", str(TOOLS / "download-dgt-pedome.py"), "--output", output]
        if mode == "pilot-authenticated":
            cmd += ["--login", "--collection", "MDT-50cm", "--collection", "MDS-50cm"]
        return cmd, None
    cmd = [sys.executable, "-u", str(TOOLS / "collect-dgt-pedome.py"), "--output", output]
    if mode == "historical":
        return cmd + ["--historical-orthos"], "geodata-dgt-history-" + snapshot
    if mode == "laz":
        cmd += ["--collection", "LAZ"]
    elif mode == "collection":
        cmd += ["--collection", collection]
    return cmd, "geodata-dgt-pedome-" + snapshot

def fingerprint(path):
    with path.open("rb") as stream:
        return {"name": path.name, "bytes": path.stat().st_size,
                "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}

def verified_files(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(manifest.get("items"), list):
        raise ValueError("Invalid expanded acquisition manifest")
    found = {}
    for entry in manifest["items"]:
        if entry.get("ok") is not True:
            continue
        name = entry.get("filename", "")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+\.(?:tif|laz)", name) or name in found:
            raise ValueError("Unsafe or duplicate filename")
        path = directory / name
        if not path.is_file() or path.is_symlink():
            raise ValueError("Missing regular file: " + name)
        with path.open("rb") as stream:
            magic = stream.read(4)
        if (path.suffix == ".tif" and magic not in TIFF) or (path.suffix == ".laz" and magic != b"LASF"):
            raise ValueError("Invalid file signature: " + name)
        fp = fingerprint(path)
        if fp["bytes"] != entry.get("bytes") or fp["sha256"] != entry.get("sha256"):
            raise ValueError("Manifest mismatch: " + name)
        if fp["bytes"] >= 2147483648:
            raise ValueError("Asset exceeds GitHub release limit: " + name)
        found[name] = fp
    if not found:
        raise ValueError("No successful files to archive")
    return found

def same_asset(asset, expected):
    return (asset.get("name") == expected["name"] and asset.get("size") == expected["bytes"]
            and asset.get("digest") == "sha256:" + expected["sha256"])

def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)

def paged(endpoint):
    for page in range(1, 101):
        data = json.loads(gh("api", endpoint + f"?per_page=100&page={page}"))
        if not isinstance(data, list):
            raise ValueError("Unexpected API response")
        yield from data
        if len(data) < 100:
            return
    raise ValueError("Pagination limit")

def draft_release(repo, tag):
    matches = [r for r in paged(f"repos/{repo}/releases") if r["tag_name"] == tag]
    if len(matches) > 1:
        raise ValueError("Duplicate release tag")
    if matches and matches[0]["draft"] is not True:
        raise ValueError("Refusing to modify a published release")
    return matches[0] if matches else None

def archive(directory, tag):
    directory = Path(directory).resolve()
    expected = verified_files(directory)
    count = len(expected)
    repo, commit = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"]
    run, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid repository or commit")
    if not run.isdigit() or not attempt.isdigit():
        raise ValueError("Invalid run identity")
    manifest = directory / f"manifest-{run}-{attempt}.json"
    manifest.write_bytes((directory / "manifest.json").read_bytes())
    expected[manifest.name] = fingerprint(manifest)
    release = draft_release(repo, tag)
    if release is None:
        gh("release", "create", tag, "--repo", repo, "--draft", "--target", commit,
           "--title", "DGT Pedome — geographic source archive",
           "--notes", "Direção-Geral do Território (DGT), WGS84 bbox -8.405,41.405,-8.375,41.435. "
           "Terms https://www.dgterritorio.gov.pt/dados-abertos ; keep unpublished until licences and owner approval are confirmed. No credentials or signed URLs.")
        release = draft_release(repo, tag)
    if release is None:
        raise ValueError("Draft release not found")
    endpoint = f"repos/{repo}/releases/{release['id']}/assets"
    assets = {a["name"]: a for a in paged(endpoint)}
    # Refuse the whole operation before uploading anything if an existing name conflicts.
    for name, fp in expected.items():
        if name in assets and not same_asset(assets[name], fp):
            raise ValueError("Existing asset differs; choose a new snapshot, never overwrite: " + name)
    for name in sorted(expected):
        if name in assets:
            print("Existing verified:", name)
            continue
        gh("release", "upload", tag, str(directory / name), "--repo", repo)
    final = draft_release(repo, tag)
    if final is None or final["id"] != release["id"]:
        raise ValueError("Draft changed")
    assets = {a["name"]: a for a in paged(endpoint)}
    for name, fp in expected.items():
        if name not in assets or not same_asset(assets[name], fp):
            raise ValueError("Uploaded asset verification failed: " + name)
    print("Archived/verified originals:", count, "tag:", tag)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("plan", "collect", "archive"))
    p.add_argument("--mode", choices=MODES, required=True)
    p.add_argument("--collection", choices=COLLECTIONS, default="MDT-50cm")
    p.add_argument("--snapshot", default="20261127")
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    cmd, tag = plan(a.mode, a.collection, a.snapshot, a.output)
    if a.action == "plan":
        print(json.dumps({"command": cmd, "draft_tag": tag}))
    elif a.action == "collect":
        return subprocess.run(cmd, check=False).returncode
    else:
        if tag is None:
            raise ValueError("Pilot probes do not archive data")
        archive(a.output, tag)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
