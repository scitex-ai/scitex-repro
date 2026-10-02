"""Compare source, wheel, sdist and installed runtime bytes without app imports."""

from __future__ import annotations

import argparse
import base64
import csv
from email.parser import Parser
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tarfile
import tomllib
import zipfile


PACKAGE = "scitex_repro"
MAX_FILES = 250
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 40 * 1024 * 1024


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and "\\" not in name


def source_files(root: Path) -> dict[str, bytes]:
    source = root / "src" / PACKAGE
    result = {}
    for path in sorted(source.rglob("*")):
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        relative = path.relative_to(root / "src").as_posix()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
            raise ValueError(f"source must be a bounded regular file: {relative}")
        if ({".doctrees", "__pycache__"} & set(path.parts)
                or path.suffix in {".pickle", ".doctree", ".pyc"}
                or path.name == ".buildinfo"):
            raise ValueError(f"build cache cannot ship as a runtime file: {relative}")
        result[relative] = path.read_bytes()
    if not result or len(result) > MAX_FILES or sum(map(len, result.values())) > MAX_TOTAL_BYTES:
        raise ValueError("runtime source exceeds its file or size bounds")
    return result


def verify_metadata(raw: bytes, project: dict) -> dict:
    metadata = Parser().parsestr(raw.decode("utf-8"))
    if metadata["Name"] != project["name"] or metadata["Version"] != project["version"]:
        raise ValueError("artifact package identity differs from source")
    if metadata["Requires-Python"] != project["requires-python"]:
        raise ValueError("artifact Python requirement differs from source")
    requirements = metadata.get_all("Requires-Dist", [])
    normalized = [item.replace(" ", "").lower() for item in requirements]
    if "scitex-logging>=0.2.2" not in normalized:
        raise ValueError("artifact lacks the genuine Logger core floor")
    if not any(item.startswith("scitex-dev>=0.62.2;") and "extra==" in item
               and "dev" in item for item in normalized):
        raise ValueError("artifact lacks the genuine Dev extra floor")
    extras = sorted(metadata.get_all("Provides-Extra", []))
    if extras != sorted(project["optional-dependencies"]):
        raise ValueError("artifact extras differ from source")
    return {"name": metadata["Name"], "version": metadata["Version"],
            "requires_python": metadata["Requires-Python"], "extras": extras,
            "requires_dist": requirements}


def read_artifacts(directory: Path, project: dict, expected: dict[str, bytes]) -> dict:
    wheels = sorted(directory.glob("*.whl"))
    sdists = sorted(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("exactly one wheel and sdist are required")
    report = {"artifact_sha256": {path.name: digest(path.read_bytes()) for path in wheels + sdists}}
    with zipfile.ZipFile(wheels[0]) as archive:
        entries = archive.infolist()
        names = [item.filename for item in entries]
        if len(names) != len(set(names)) or not all(map(safe_name, names)):
            raise ValueError("wheel contains duplicate or unsafe member names")
        if sum(item.file_size for item in entries) > 2 * MAX_TOTAL_BYTES:
            raise ValueError("wheel exceeds its uncompressed bound")
        actual = {}
        for item in entries:
            if item.filename.startswith(PACKAGE + "/") and not item.is_dir():
                if item.file_size > MAX_FILE_BYTES or stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError("wheel runtime member is oversized or a symlink")
                actual[item.filename] = archive.read(item)
        if actual != expected:
            raise ValueError("wheel runtime bytes differ from source")
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise ValueError("wheel must have exactly one metadata owner")
        report["wheel_metadata"] = verify_metadata(archive.read(metadata_names[0]), project)
    with tarfile.open(sdists[0]) as archive:
        entries = archive.getmembers()
        names = [item.name for item in entries]
        if len(names) != len(set(names)) or not all(map(safe_name, names)):
            raise ValueError("sdist contains duplicate or unsafe member names")
        if sum(item.size for item in entries) > 2 * MAX_TOTAL_BYTES:
            raise ValueError("sdist exceeds its uncompressed bound")
        top = f"scitex_repro-{project['version']}/"
        actual = {}
        for item in entries:
            if item.name.startswith(top + "src/" + PACKAGE + "/") and not item.isdir():
                if not item.isfile() or item.size > MAX_FILE_BYTES:
                    raise ValueError("sdist runtime member must be bounded and regular")
                actual[item.name[len(top + "src/"):]] = archive.extractfile(item).read()
        if actual != expected:
            raise ValueError("sdist runtime bytes differ from source")
        report["sdist_metadata"] = verify_metadata(archive.extractfile(top + "PKG-INFO").read(), project)
    return report


def verify_installed(site: Path, project: dict, expected: dict[str, bytes]) -> dict:
    owners = [item for item in importlib.metadata.distributions(path=[str(site)])
              if item.metadata["Name"] == project["name"]]
    if len(owners) != 1 or owners[0].version != project["version"]:
        raise ValueError("installed package must have one exact metadata owner")
    owner = owners[0]
    metadata = verify_metadata(owner.read_text("METADATA").encode(), project)
    records = {}
    for row in csv.reader(io.StringIO(owner.read_text("RECORD"))):
        if row[0] in records:
            raise ValueError("installed RECORD contains duplicate members")
        records[row[0]] = row[1:]
    recorded_runtime = {name for name in records if name.startswith(PACKAGE + "/")}
    recorded_runtime = {name for name in recorded_runtime if not name.endswith(".pyc")}
    if recorded_runtime != set(expected):
        raise ValueError("installed RECORD runtime membership differs from source")
    for name, content in expected.items():
        path = site / name
        if path.is_symlink() or not path.resolve().is_relative_to(site.resolve()):
            raise ValueError("installed runtime escaped its owned site")
        if path.read_bytes() != content:
            raise ValueError(f"installed runtime differs from source: {name}")
        encoded = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
        if records[name] != ["sha256=" + encoded, str(len(content))]:
            raise ValueError(f"installed RECORD hash/size differs from source: {name}")
    if PACKAGE in sys.modules:
        raise ValueError("metadata verifier imported the application")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="store_true")
    parser.add_argument("--dist", type=Path)
    parser.add_argument("--installed", type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    expected = source_files(root)
    if args.source:
        tag = "v" + project["version"]
        ref = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        tagged = subprocess.check_output(["git", "rev-parse", tag + "^{commit}"], text=True).strip()
        if tagged != ref:
            raise ValueError("source must be the exact version-tagged commit")
    report = {"name": project["name"], "version": project["version"],
              "runtime_files": len(expected),
              "runtime_sha256": {name: digest(content) for name, content in expected.items()}}
    if args.dist:
        report.update(read_artifacts(args.dist, project, expected))
    if args.installed:
        report["installed_metadata"] = verify_installed(args.installed, project, expected)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
