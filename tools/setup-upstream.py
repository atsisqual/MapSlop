#!/usr/bin/env python3
"""Fetch and verify the same two upstream commits used by Pages."""
import argparse
import pathlib
import shutil
import subprocess
import tempfile

NAIROBI = ("https://github.com/briankariuki/slop-nairobi.git",
           "64b8599ae7dd7ba56ffbe68f19cc1423a9e7f903")
THREE = ("https://github.com/mrdoob/three.js.git",
         "f17eb5d689094a3fbd4cd0d64d54729a48036ce0")

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

def checkout(path, source, sparse=()):
    url, commit = source
    if not path.exists():
        with tempfile.TemporaryDirectory(dir=path.parent, prefix="fetch-") as temp:
            working = pathlib.Path(temp) / "repo"
            working.mkdir()
            git(working, "init")
            git(working, "remote", "add", "origin", url)
            if sparse:
                git(working, "sparse-checkout", "set", *sparse)
            args = ["fetch", "--depth=1"]
            if sparse:
                args.append("--filter=blob:none")
            git(working, *args, "origin", commit)
            git(working, "checkout", "--detach", "FETCH_HEAD")
            if git(working, "rev-parse", "HEAD") != commit:
                raise RuntimeError("Unexpected source commit")
            working.rename(path)
    if git(path, "rev-parse", "HEAD") != commit or git(path, "remote", "get-url", "origin") != url:
        raise RuntimeError(f"Unexpected checkout {path}; inspect it or choose a new cache")
    if git(path, "status", "--porcelain"):
        raise RuntimeError(f"Modified upstream checkout {path}; refusing to overwrite")
    print(path, commit)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cache", type=pathlib.Path)
    args = parser.parse_args()
    cache = args.cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    checkout(cache / "nairobi", NAIROBI)
    checkout(cache / "three", THREE, ("build", "examples/jsm"))
    vendor = cache / "three-vendor"
    if not vendor.exists():
        with tempfile.TemporaryDirectory(dir=cache, prefix="vendor-") as temp:
            working = pathlib.Path(temp) / "three-vendor"
            working.mkdir()
            for folder in ("build", "examples"):
                shutil.copytree(cache / "three" / folder, working / folder)
            shutil.copy2(cache / "three" / "LICENSE", working / "LICENSE")
            (working / ".upstream-commit").write_text(THREE[1] + "\n", encoding="utf-8")
            working.rename(vendor)
    if (vendor / ".upstream-commit").read_text().strip() != THREE[1]:
        raise RuntimeError("Unexpected Three.js vendor cache")
    for required in ("LICENSE", "build/three.webgpu.js", "build/three.tsl.js", "examples/jsm"):
        if not (vendor / required).exists():
            raise RuntimeError(f"Incomplete Three.js vendor cache: {required}")
    print("Pinned upstreams ready")

if __name__ == "__main__":
    main()
