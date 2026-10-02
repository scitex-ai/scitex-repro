#!/usr/bin/env python3
"""Stage bounded Sphinx HTML for review before an ordinary documentation PR.

This validates file types, sizes and source identity. Content still needs review
before publication; a digest manifest does not establish that content is public.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tomllib


MAX_FILES = 200
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
ASSET_SUFFIXES = {".html", ".css", ".js", ".svg", ".png", ".jpg", ".jpeg",
                  ".gif", ".ico", ".woff", ".woff2", ".eot", ".ttf"}


def _regular_bytes(path: Path, limit: int) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ValueError(f"not a bounded regular file: {path}")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        content = stream.read(limit + 1)
    if len(content) != info.st_size or len(content) > limit:
        raise ValueError(f"file changed or exceeded its bound: {path}")
    return content


def collect_html(html: Path) -> tuple[list[tuple[str, bytes]], list[str]]:
    if not stat.S_ISDIR(html.lstat().st_mode):
        raise ValueError("HTML root must be a real directory")
    selected = []
    excluded = []
    total = 0
    for directory, directories, files in os.walk(html, followlinks=False):
        root = Path(directory)
        for name in sorted(directories):
            child = root / name
            if not stat.S_ISDIR(child.lstat().st_mode):
                raise ValueError(f"non-directory in HTML tree: {child}")
            if name == ".doctrees":
                directories.remove(name)
                excluded.append(child.relative_to(html).as_posix() + "/")
        directories.sort()
        for name in sorted(files):
            child = root / name
            relative = child.relative_to(html).as_posix()
            if not stat.S_ISREG(child.lstat().st_mode):
                raise ValueError(f"non-regular HTML entry: {relative}")
            if relative == ".buildinfo":
                excluded.append(relative)
                continue
            if relative == ".nojekyll":
                if _regular_bytes(child, MAX_FILE_BYTES):
                    raise ValueError(".nojekyll must be empty")
                continue
            allowed = (child.suffix in ASSET_SUFFIXES or relative == "objects.inv"
                       or (relative.startswith("_sources/") and relative.endswith(".txt")))
            if not allowed:
                raise ValueError(f"unexpected HTML artifact type: {relative}")
            content = _regular_bytes(child, MAX_FILE_BYTES)
            total += len(content)
            selected.append((relative, content))
            if len(selected) >= MAX_FILES or total > MAX_TOTAL_BYTES:
                raise ValueError("HTML artifact exceeds its file or total-size bound")
    if "index.html" not in {name for name, _ in selected}:
        raise ValueError("HTML artifact has no index.html")
    return sorted(selected + [(".nojekyll", b"")]), sorted(excluded)


def stage_bundle(html: Path, destination: Path, source: dict) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", source.get("commit", "")):
        raise ValueError("source commit must be a full Git SHA")
    if destination.exists() or destination.is_symlink():
        raise ValueError("artifact destination must be fresh")
    files, excluded = collect_html(html)
    manifest = {
        "schema": 1,
        "package": "scitex-repro",
        "source": source,
        "limits": {"files": MAX_FILES, "file_bytes": MAX_FILE_BYTES,
                   "total_bytes": MAX_TOTAL_BYTES},
        "excluded_build_cache_paths": excluded,
        "files": [{"path": name, "bytes": len(content),
                   "sha256": hashlib.sha256(content).hexdigest()}
                  for name, content in files],
    }
    destination.mkdir()
    bundle = destination / "bundle"
    bundle.mkdir()
    for name, content in files:
        target = bundle / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (destination / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest


def source_identity(checkout: Path, expected_commit: str) -> dict:
    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(checkout), *args])

    commit = git("rev-parse", "HEAD").decode().strip()
    if commit != expected_commit or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("checkout does not match the expected source commit")
    tracked = git("ls-tree", "-r", "-z", commit, "--", "docs/sphinx",
                  "src/scitex_repro", "pyproject.toml")
    inventory = []
    for row in tracked.split(b"\0"):
        if not row:
            continue
        metadata, path_bytes = row.split(b"\t", 1)
        mode, kind, _ = metadata.split()
        path = path_bytes.decode("utf-8")
        if path.startswith(("src/scitex_repro/_sphinx_html/",
                            "docs/sphinx/_build/", "docs/sphinx/to_claude/")):
            continue
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            raise ValueError(f"source must be a tracked regular file: {path}")
        content = _regular_bytes(checkout / path, MAX_FILE_BYTES)
        if content != git("show", f"{commit}:{path}"):
            raise ValueError(f"source differs from its commit: {path}")
        inventory.append({"path": path, "bytes": len(content),
                          "sha256": hashlib.sha256(content).hexdigest()})
    project = tomllib.loads((checkout / "pyproject.toml").read_text())["project"]
    if project["name"] != "scitex-repro":
        raise ValueError("unexpected source project")
    return {"commit": commit, "version": project["version"], "files": inventory}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    checkout = Path.cwd()
    manifest = stage_bundle(checkout / "docs/sphinx/_build/html",
                            checkout / "docs-bundle-artifact",
                            source_identity(checkout, args.source_sha))
    print(f"Staged {len(manifest['files'])} files for review from "
          f"{manifest['source']['commit']}; no branch was published.")


if __name__ == "__main__":
    main()
