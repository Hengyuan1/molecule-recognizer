"""Committed-source packaging and archived Git validation, without network."""

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import zipfile

import pytest


@pytest.fixture
def release_modules(monkeypatch):
    directory = Path(__file__).resolve().parents[1] / "packaging/windows"
    monkeypatch.syspath_prepend(str(directory))

    def load(name):
        spec = importlib.util.spec_from_file_location(name, directory / f"{name}.py")
        result = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(result)
        return result

    return load


def source_manifest(directory, names=("source.tar.gz",)):
    records = []
    for name in names:
        path = directory / name
        path.write_bytes(b"inventoried original input")
        records.append({"archive": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "resolved_url": "https://example.org/source?temporary=token"})
    manifest = directory / "inputs.json"
    manifest.write_text(json.dumps({"archives": records}))
    return manifest


@pytest.mark.parametrize("name", ["../source", "/source", "x\\source", "C:/source", "", ".", "a//b", "./a"])
def test_source_inventory_refuses_unsafe_paths(tmp_path, release_modules, name):
    manifest = tmp_path / "inputs.json"
    manifest.write_text(json.dumps({"archives": [{"archive": name, "sha256": "0" * 64}]}))
    with pytest.raises(ValueError, match="Unsafe"):
        release_modules("package_sources").inventory(tmp_path, [manifest])


def test_source_inventory_checks_hashes_and_deduplicates(tmp_path, release_modules):
    manifest = source_manifest(tmp_path)
    packager = release_modules("package_sources")
    records = packager.inventory(tmp_path, [manifest, manifest])
    assert len(records) == 1
    assert records[0]["resolved_url"] == "https://example.org/source"
    (tmp_path / "source.tar.gz").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum"):
        packager.inventory(tmp_path, [manifest])


def test_source_inventory_rejects_case_collisions(tmp_path, release_modules):
    manifest = source_manifest(tmp_path, ("source.tar.gz", "Source.tar.gz"))
    with pytest.raises(ValueError, match="collision"):
        release_modules("package_sources").inventory(tmp_path, [manifest])


@pytest.fixture
def committed_tree(tmp_path, monkeypatch):
    if not shutil.which("git"):
        pytest.skip("Git required for committed-tree checks")
    for key in list(os.environ):
        if key.startswith("GIT_"):
            monkeypatch.delenv(key)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    repository = tmp_path / "repository"
    repository.mkdir()
    template = tmp_path / "empty-template"
    template.mkdir()

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=repository, stderr=subprocess.PIPE)

    git("init", f"--template={template}")
    guide = repository / "packaging/windows/SOURCE-README.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("Committed source guide\n")
    (repository / "app.txt").write_text("committed application\n")
    git("add", "app.txt", "packaging/windows/SOURCE-README.md")
    git("-c", "user.name=Release Test", "-c", "user.email=test@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "-m", "test tree")
    revision = git("rev-parse", "HEAD").decode().strip()
    return repository, revision, git


def test_package_uses_commit_not_dirty_or_untracked_files(tmp_path, release_modules, committed_tree):
    repository, revision, _ = committed_tree
    (repository / "app.txt").write_text("dirty local change")
    (repository / "private.txt").write_text("never package this")
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    manifest = source_manifest(source_dir)
    packager = release_modules("package_sources")
    output = tmp_path / "output"
    path = packager.package(source_dir, [manifest], output, revision, "0.3.0", repository)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        prefix = "MolRecognizer-0.3.0-sources/"
        record = json.loads(archive.read(prefix + "SOURCES.json"))
        assert record["app_revision"] == revision
        assert record["license_review_complete"] is False
        assert archive.read(prefix + "README.md") == b"Committed source guide\n"
        app = archive.read(prefix + "molrecognizer-source.tar.gz")
        assert hashlib.sha256(app).hexdigest() == record["application_source"]["sha256"]
        with tarfile.open(fileobj=io.BytesIO(app)) as tree:
            assert "molrecognizer/private.txt" not in tree.getnames()
            assert tree.extractfile("molrecognizer/app.txt").read() == b"committed application\n"
    assert path.with_suffix(".zip.sha256").read_text().split()[0] == packager.sha256(path)
    with pytest.raises(FileExistsError):
        packager.package(source_dir, [manifest], output, revision, "0.3.0", repository)


@pytest.mark.parametrize("revision,version", [("main", "0.3.0"), ("a" * 40, "0.3.0rc1")])
def test_packaging_requires_commit_and_stable_version(tmp_path, release_modules, revision, version):
    with pytest.raises(ValueError):
        release_modules("package_sources").package(tmp_path, [], tmp_path, revision, version, tmp_path)


def git_container(path, repository, *, extra=None):
    with tarfile.open(path, "w") as archive:
        for source in (repository / ".git/objects").rglob("*"):
            if source.is_file():
                name = source.relative_to(repository / ".git").as_posix()
                archive.add(source, "example/repository/" + name)
        # These are not copied into the verifier's fresh repository.
        payloads = {"example/repository/config": b"untrusted archived configuration",
                    "example/repository/hooks/pre-commit": b"untrusted archived hook"}
        payloads.update(extra or {})
        for name, payload in payloads.items():
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))


def test_vcs_reads_pinned_tree_without_archived_config(tmp_path, release_modules, committed_tree):
    repository, revision, git = committed_tree
    path = tmp_path / "container.tar"
    git_container(path, repository)
    expected = hashlib.sha256(git("archive", "--format=tar", revision)).hexdigest()
    request = {"file": "repository", "source": "git+https://example.org/repo#commit=" + revision,
               "declared_checksums": {"sha256": expected}}
    checker = release_modules("verify_vcs_sources")
    result = checker.verify_git(path, "example", request)
    assert result["matches_declared_sha256"]
    assert result["commit"] == revision
    request["declared_checksums"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        checker.verify_git(path, "example", request)


def test_vcs_rejects_archived_alternates(tmp_path, release_modules, committed_tree):
    repository, revision, _ = committed_tree
    path = tmp_path / "container.tar"
    git_container(path, repository, extra={"example/repository/objects/info/alternates": b"/outside"})
    with pytest.raises(ValueError, match="Unexpected Git object"):
        release_modules("verify_vcs_sources").verify_git(path, "example", {
            "file": "repository", "source": "git+https://example.org/repo#commit=" + revision})
