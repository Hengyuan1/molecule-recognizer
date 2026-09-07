"""Release-source collection and Qt-payload policy without Windows or network."""

import importlib.util
import io
import json
from pathlib import Path
import tarfile

import pytest


def module(name):
    path = Path(__file__).resolve().parents[1] / "packaging/windows" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize("path", ["PySide6/Qt6VirtualKeyboard.dll",
                                    "PySide6\\plugins\\imageformats\\qpdf.dll",
                                    "PySide6/Qt6QmlModels.dll", "PySide6/opengl32sw.dll"])
def test_unused_qt_components_are_excluded(path):
    assert not module("release_checks").include_binary(path)


@pytest.mark.parametrize("path", ["PySide6/Qt6Core.dll", "PySide6/plugins/platforms/qwindows.dll",
                                    "PySide6/plugins/imageformats/qtiff.dll", "tools/osra/bin/qpdf.dll"])
def test_qt_filter_is_scoped_and_keeps_needed_plugins(path):
    assert module("release_checks").include_binary(path)


def test_revision_requires_full_commit_hash():
    checks = module("release_checks")
    assert checks.require_source_revision(None) is None
    assert checks.require_source_revision("a" * 40) == "a" * 40
    for value in ("main", "abcdef", "a" * 39, "A" * 40):
        with pytest.raises(ValueError):
            checks.require_source_revision(value)


def test_sources_include_exact_package_revision_and_deduplicate():
    fetcher = module("fetch_release_sources")
    package = {"base": ["mingw-w64-example"], "version": ["1.2.3-4"], "licenses": ["MIT"]}
    requests = fetcher.source_requests({"msys2_packages": [package, package]}, "6.11.0")
    assert len(requests) == 5
    assert requests[0]["archive"] == "mingw-w64-example-1.2.3-4.src.tar.zst"
    assert {item["component"] for item in requests[1:]} == {"qtbase", "qtsvg", "qtimageformats", "pyside-setup"}
    assert all(item["url"].startswith("https://") for item in requests)


def test_source_download_cache_detects_modified_archives(tmp_path):
    fetcher = module("fetch_release_sources")
    request = {"archive": "example.tar.xz", "url": "https://example.org/example.tar.xz"}
    destination = tmp_path / request["archive"]
    destination.write_bytes(b"original")
    with pytest.raises(ValueError, match="receipt"):
        fetcher.fetch_one(request, tmp_path)
    receipt = {**request, "sha256": fetcher.sha256(destination)}
    destination.with_name(destination.name + ".json").write_text(json.dumps(receipt))
    assert fetcher.fetch_one(request, tmp_path) == receipt
    destination.write_bytes(b"modified")
    with pytest.raises(ValueError, match="differs"):
        fetcher.fetch_one(request, tmp_path)


@pytest.mark.parametrize("qt_version", ["6.11", "../6.11.0", "6.11.0/extra"])
def test_source_versions_cannot_escape_cache(qt_version):
    with pytest.raises(ValueError):
        module("fetch_release_sources").source_requests({"msys2_packages": []}, qt_version)


def test_qt_payload_must_have_required_libraries(tmp_path):
    with pytest.raises(ValueError, match="Missing required Qt"):
        module("release_checks").validate_qt_payload(tmp_path)


def test_qt_payload_rejects_unexpected_module(tmp_path):
    qt = tmp_path / "_internal/PySide6"
    qt.mkdir(parents=True)
    (qt / "Qt6VirtualKeyboard.dll").touch()
    with pytest.raises(ValueError, match="Unneeded Qt"):
        module("release_checks").validate_qt_payload(tmp_path)


def qt_archive(path, files):
    with tarfile.open(path, "w:xz") as archive:
        for name, content in files.items():
            payload = content.encode()
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))


def test_inspector_preserves_referenced_notices_and_literal_newlines(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "packaging/windows"))
    inspector = module("inspect_release_sources")
    archive = tmp_path / "qt.tar.xz"
    qt_archive(archive, {
        "qt/LICENSES/LGPL-3.0-only.txt": "original license text",
        "qt/src/3rdparty/font/qt_attribution.json":
            '{"LicenseFile": "FTL.TXT", "Copyright": "line one\nline two"}',
        "qt/src/3rdparty/font/FTL.TXT": "original font terms",
        "qt/tests/qt_attribution.json": "intentionally invalid test JSON",
    })
    result = inspector.inspect_qt(archive, "qtbase", tmp_path / "notices")
    assert "qtbase/src/3rdparty/font/FTL.TXT" in result["notices"]
    assert (tmp_path / "notices/qtbase/src/3rdparty/font/FTL.TXT").read_text() == "original font terms"


def test_inspector_rejects_license_path_traversal(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "packaging/windows"))
    archive = tmp_path / "qt.tar.xz"
    qt_archive(archive, {"../../LICENSE.txt": "not a valid archive path"})
    with pytest.raises(ValueError, match="Unsafe archive path"):
        module("inspect_release_sources").inspect_qt(archive, "qtbase", tmp_path / "notices")
    assert not (tmp_path / "LICENSE.txt").exists()
