"""Release ZIP verification without executing binaries or requiring Windows."""

import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest


@pytest.fixture
def validator(monkeypatch):
    directory = Path(__file__).resolve().parents[1] / "packaging/windows"
    monkeypatch.syspath_prepend(str(directory))
    spec = importlib.util.spec_from_file_location("validate_release", directory / "validate_release.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize("name", ["other/app.exe", "MolRecognizer/../secret", "MolRecognizer/C:/secret",
                                  "MolRecognizer/x\\secret", "MolRecognizer/./app.exe",
                                  "MolRecognizer/path /app.exe", "MolRecognizer/file."])
def test_zip_paths_cannot_escape_or_change_on_windows(tmp_path, validator, name):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        # ZipInfo normalizes separators on Windows during construction. Put
        # the literal malformed path in the ZIP, not its already-safe version.
        member = zipfile.ZipInfo("placeholder")
        member.filename = name
        archive.writestr(member, b"bad")
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="Unsafe"):
        validator.verified_members(archive, "MolRecognizer/")


def test_zip_rejects_case_collisions(tmp_path, validator):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("MolRecognizer/app.exe", b"one")
        archive.writestr("MolRecognizer/APP.exe", b"two")
    with zipfile.ZipFile(path) as archive, pytest.raises(ValueError, match="Duplicate"):
        validator.verified_members(archive, "MolRecognizer/")


def test_zip_rejects_symlinks_before_extracting(tmp_path, validator):
    path = tmp_path / "bad.zip"
    member = zipfile.ZipInfo("MolRecognizer/link")
    member.external_attr = 0o120777 << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member, b"/outside")
    output = tmp_path / "extracted"
    with pytest.raises(ValueError, match="Unsafe"):
        validator.extract_checked(path, output)
    assert not output.exists()


def test_extracted_bytes_match_and_existing_folder_is_preserved(tmp_path, validator):
    path = tmp_path / "app.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("MolRecognizer/app.exe", b"test PE placeholder")
        archive.writestr("MolRecognizer/licenses/notice.txt", b"original notice")
    output = tmp_path / "extracted"
    bundle, count = validator.extract_checked(path, output)
    assert count == 2 and (bundle / "app.exe").read_bytes() == b"test PE placeholder"
    with pytest.raises(FileExistsError):
        validator.extract_checked(path, output)


def test_zip_checksum_must_match_name_and_bytes(tmp_path, validator):
    path = tmp_path / "app.zip"
    path.write_bytes(b"zip fixture")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = path.with_suffix(".zip.sha256")
    receipt.write_text(f"{digest}  {path.name}\n", encoding="ascii")
    assert validator.verify_checksum(path) == digest
    receipt.write_text(f"{digest}  other.zip\n", encoding="ascii")
    with pytest.raises(ValueError, match="mismatch"):
        validator.verify_checksum(path)


def source_zip(path, *, extra=False, corrupt=False):
    prefix = "MolRecognizer-0.3.0-sources/"
    manifest = {"version": "0.3.0", "app_revision": "a" * 40,
                "application_source": {"archive": "app.tar.gz", "sha256": hashlib.sha256(b"app").hexdigest()},
                "archives": [{"archive": "dependency.tar.gz", "sha256": hashlib.sha256(b"source").hexdigest()}]}
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(prefix + "SOURCES.json", json.dumps(manifest))
        archive.writestr(prefix + "README.md", "source access")
        archive.writestr(prefix + "app.tar.gz", b"app")
        archive.writestr(prefix + "archives/dependency.tar.gz", b"changed" if corrupt else b"source")
        if extra:
            archive.writestr(prefix + "private.txt", b"must not be published")


def test_source_and_binary_revision_must_match(tmp_path, validator):
    path = tmp_path / "source.zip"
    source_zip(path)
    result = validator.verify_source_zip(path, "0.3.0", "a" * 40)
    assert result["archives_checked"] == 2
    with pytest.raises(ValueError, match="revision mismatch"):
        validator.verify_source_zip(path, "0.3.0", "b" * 40)


@pytest.mark.parametrize("change", ["extra", "corrupt"])
def test_source_zip_rejects_changed_or_unlisted_contents(tmp_path, validator, change):
    path = tmp_path / "source.zip"
    source_zip(path, **{change: True})
    with pytest.raises(ValueError):
        validator.verify_source_zip(path, "0.3.0", "a" * 40)
