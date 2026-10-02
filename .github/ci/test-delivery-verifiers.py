"""Stdlib synthetic controls; never import Repro or execute a package auditor."""

import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile


HERE = Path(__file__).parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


docs = load("docs_verifier", "stage-docs-bundle.py")
dist = load("dist_verifier", "check-dist.py")
COMMIT = "a" * 40
PROJECT = {"name": "scitex-repro", "version": "0.1.8", "requires-python": ">=3.10",
           "optional-dependencies": {"all": [], "dev": []}}
METADATA = ("Metadata-Version: 2.4\nName: scitex-repro\nVersion: 0.1.8\n"
            "Requires-Python: >=3.10\nProvides-Extra: all\nProvides-Extra: dev\n"
            "Requires-Dist: scitex-logging>=0.2.2\n"
            "Requires-Dist: scitex-dev>=0.62.2; extra == 'dev'\n\n").encode()
RUNTIME = {"scitex_repro/__init__.py": b"public synthetic source\n",
           "scitex_repro/_sphinx_html/index.html": b"<html>public fixture</html>"}


class DocsControls(unittest.TestCase):
    def setUp(self):
        self.context = tempfile.TemporaryDirectory()
        self.addCleanup(self.context.cleanup)
        self.root = Path(self.context.name)
        self.html = self.root / "html"
        self.html.mkdir()
        (self.html / "index.html").write_bytes(b"<html>public synthetic fixture</html>")
        self.destination = self.root / "artifact"

    def stage(self):
        return docs.stage_bundle(self.html, self.destination, {"commit": COMMIT})

    def test_exact_renderable_bytes_and_hashes(self):
        manifest = self.stage()
        rows = {row["path"]: row for row in manifest["files"]}
        content = (self.html / "index.html").read_bytes()
        self.assertEqual((self.destination / "bundle/index.html").read_bytes(), content)
        self.assertEqual(rows["index.html"]["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(rows["index.html"]["bytes"], len(content))
        self.assertEqual((self.destination / "bundle/.nojekyll").read_bytes(), b"")
        self.assertEqual(json.loads((self.destination / "manifest.json").read_text()), manifest)

    def test_assets_sources_and_inventory_retained(self):
        (self.html / "_sources").mkdir()
        (self.html / "_sources/index.rst.txt").write_text("public fixture")
        (self.html / "objects.inv").write_bytes(b"synthetic inventory")
        for suffix in sorted(docs.ASSET_SUFFIXES):
            (self.html / ("asset" + suffix)).write_bytes(b"public synthetic asset")
        manifest = self.stage()
        self.assertEqual(len(manifest["files"]), len(docs.ASSET_SUFFIXES) + 4)

    def test_caches_excluded_without_unpickling(self):
        (self.html / ".doctrees").mkdir()
        (self.html / ".doctrees/environment.pickle").write_bytes(b"invalid pickle")
        (self.html / ".buildinfo").write_text("build-only metadata")
        manifest = self.stage()
        self.assertEqual(manifest["excluded_build_cache_paths"], [".buildinfo", ".doctrees/"])
        self.assertEqual(len(manifest["files"]), 2)

    def test_file_symlink_refused(self):
        (self.html / "linked.html").symlink_to("index.html")
        with self.assertRaises(ValueError): self.stage()
        self.assertFalse(self.destination.exists())

    def test_directory_symlink_refused(self):
        (self.html / "linked-directory").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): self.stage()

    def test_root_symlink_refused(self):
        linked = self.root / "linked"
        linked.symlink_to(self.html, target_is_directory=True)
        with self.assertRaises(ValueError):
            docs.stage_bundle(linked, self.destination, {"commit": COMMIT})

    def test_unknown_file_type_refused(self):
        (self.html / "environment.pickle").write_bytes(b"invalid pickle")
        with self.assertRaises(ValueError): self.stage()

    def test_text_outside_sources_refused(self):
        (self.html / "arbitrary.txt").write_text("fixture")
        with self.assertRaises(ValueError): self.stage()

    def test_nonempty_nojekyll_refused(self):
        (self.html / ".nojekyll").write_text("unexpected content")
        with self.assertRaises(ValueError): self.stage()

    def test_missing_index_refused(self):
        (self.html / "index.html").unlink()
        with self.assertRaises(ValueError): self.stage()

    def test_existing_destination_preserved(self):
        self.destination.mkdir()
        sentinel = self.destination / "sentinel"
        sentinel.write_text("preserve")
        with self.assertRaises(ValueError): self.stage()
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_invalid_source_commit_refused(self):
        with self.assertRaises(ValueError):
            docs.stage_bundle(self.html, self.destination, {"commit": "main"})

    def test_individual_size_bound(self):
        with patch.object(docs, "MAX_FILE_BYTES", 1):
            with self.assertRaises(ValueError): self.stage()

    def test_total_size_bound(self):
        with patch.object(docs, "MAX_TOTAL_BYTES", 1):
            with self.assertRaises(ValueError): self.stage()

    def test_count_bound_includes_nojekyll(self):
        with patch.object(docs, "MAX_FILES", 1):
            with self.assertRaises(ValueError): self.stage()

    def test_head_mismatch_refused_before_source_reads(self):
        with patch.object(docs.subprocess, "check_output", return_value=("b" * 40).encode()):
            with self.assertRaises(ValueError): docs.source_identity(self.root, COMMIT)


class DistControls(unittest.TestCase):
    def setUp(self):
        self.context = tempfile.TemporaryDirectory()
        self.addCleanup(self.context.cleanup)
        self.root = Path(self.context.name)
        self.artifacts = self.root / "dist"
        self.artifacts.mkdir()

    def build(self, runtime=None, metadata=METADATA, extra_wheel=None, extra_sdist=None):
        runtime = RUNTIME if runtime is None else runtime
        wheel = self.artifacts / "scitex_repro-0.1.8-py3-none-any.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            for name, content in runtime.items(): archive.writestr(name, content)
            archive.writestr("scitex_repro-0.1.8.dist-info/METADATA", metadata)
            if extra_wheel: archive.writestr(*extra_wheel)
        sdist = self.artifacts / "scitex_repro-0.1.8.tar.gz"
        with tarfile.open(sdist, "w:gz") as archive:
            rows = [("scitex_repro-0.1.8/src/" + name, content) for name, content in runtime.items()]
            rows.append(("scitex_repro-0.1.8/PKG-INFO", metadata))
            if extra_sdist: rows.append(extra_sdist)
            for name, content in rows:
                info = tarfile.TarInfo(name)
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))

    def test_exact_wheel_sdist_runtime_and_metadata(self):
        self.build()
        report = dist.read_artifacts(self.artifacts, PROJECT, RUNTIME)
        self.assertEqual(report["wheel_metadata"]["version"], "0.1.8")
        self.assertEqual(len(report["artifact_sha256"]), 2)

    def test_changed_runtime_refused(self):
        self.build(runtime={**RUNTIME, "scitex_repro/__init__.py": b"changed"})
        with self.assertRaises(ValueError): dist.read_artifacts(self.artifacts, PROJECT, RUNTIME)

    def test_extra_runtime_refused(self):
        self.build(extra_wheel=("scitex_repro/unexpected.py", b"extra"))
        with self.assertRaises(ValueError): dist.read_artifacts(self.artifacts, PROJECT, RUNTIME)

    def test_missing_artifact_refused(self):
        self.build()
        next(self.artifacts.glob("*.tar.gz")).unlink()
        with self.assertRaises(ValueError): dist.read_artifacts(self.artifacts, PROJECT, RUNTIME)

    def test_duplicate_wheel_artifact_refused(self):
        self.build()
        (self.artifacts / "other.whl").write_bytes(b"fixture")
        with self.assertRaises(ValueError): dist.read_artifacts(self.artifacts, PROJECT, RUNTIME)

    def test_traversal_wheel_member_refused(self):
        self.build(extra_wheel=("../escape", b"fixture"))
        with self.assertRaises(ValueError): dist.read_artifacts(self.artifacts, PROJECT, RUNTIME)

    def test_traversal_sdist_member_refused(self):
        self.build(extra_sdist=("scitex_repro-0.1.8/../escape", b"fixture"))
        with self.assertRaises(ValueError): dist.read_artifacts(self.artifacts, PROJECT, RUNTIME)

    def test_wrong_version_refused(self):
        self.build(metadata=METADATA.replace(b"Version: 0.1.8", b"Version: 0.1.7"))
        with self.assertRaises(ValueError): dist.read_artifacts(self.artifacts, PROJECT, RUNTIME)

    def test_core_floor_missing_refused(self):
        self.build(metadata=METADATA.replace(b"scitex-logging>=0.2.2", b"scitex-logging"))
        with self.assertRaises(ValueError): dist.read_artifacts(self.artifacts, PROJECT, RUNTIME)

    def test_extra_set_mismatch_refused(self):
        self.build(metadata=METADATA.replace(b"Provides-Extra: dev\n", b""))
        with self.assertRaises(ValueError): dist.read_artifacts(self.artifacts, PROJECT, RUNTIME)

    def test_source_build_cache_refused(self):
        source = self.root / "src/scitex_repro/.doctrees"
        source.mkdir(parents=True)
        (source / "environment.pickle").write_bytes(b"invalid pickle")
        with self.assertRaises(ValueError): dist.source_files(self.root)

    def test_installed_bytes_and_record(self):
        self.installed()
        metadata = dist.verify_installed(self.root / "site", PROJECT, RUNTIME)
        self.assertEqual(metadata["name"], "scitex-repro")

    def installed(self):
        site = self.root / "site"
        site.mkdir()
        rows = []
        for name, content in RUNTIME.items():
            target = site / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            encoded = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
            rows.append(f"{name},sha256={encoded},{len(content)}")
        metadata = site / "scitex_repro-0.1.8.dist-info"
        metadata.mkdir()
        (metadata / "METADATA").write_bytes(METADATA)
        (metadata / "RECORD").write_text("\n".join(rows) + "\n")

    def test_installed_record_mismatch_refused(self):
        self.installed()
        record = self.root / "site/scitex_repro-0.1.8.dist-info/RECORD"
        record.write_text(record.read_text().replace("sha256=", "sha256=wrong"))
        with self.assertRaises(ValueError): dist.verify_installed(self.root / "site", PROJECT, RUNTIME)

    def test_installed_runtime_symlink_refused(self):
        self.installed()
        target = self.root / "site/scitex_repro/__init__.py"
        content = target.read_bytes()
        target.unlink()
        external = self.root / "external"
        external.write_bytes(content)
        target.symlink_to(external)
        with self.assertRaises(ValueError): dist.verify_installed(self.root / "site", PROJECT, RUNTIME)


if __name__ == "__main__":
    unittest.main(verbosity=2)
