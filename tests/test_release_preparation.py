"""Release-source collection and Qt-payload policy without Windows or network."""

import importlib.util
import hashlib
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


def packaging_module(name, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "packaging/windows"))
    return module(name)


def test_source_receipts_do_not_publish_signed_download_parameters():
    assert module("fetch_release_sources").public_origin(
        "https://example.org/source.zip?sig=temporary&jwt=temporary#fragment"
    ) == "https://example.org/source.zip"


@pytest.mark.parametrize("name", ["../file.tar.gz", "/file.tar.gz", "x\\file.zip", "x:foo.zip", "file.html"])
def test_additional_source_request_rejects_unsafe_names(name, monkeypatch):
    with pytest.raises(ValueError, match="Unsafe"):
        packaging_module("collect_additional_sources", monkeypatch).validate_request(
            {"archive": name, "url": "https://example.org/source"})


def test_additional_source_checks_declared_hash_and_container(tmp_path, monkeypatch):
    collector = packaging_module("collect_additional_sources", monkeypatch)
    path = tmp_path / "source.tar.xz"
    qt_archive(path, {"source/LICENSE": "original"})
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert collector.check_archive(path, {"expected_hashes": {"sha256": digest}}) == 1
    with pytest.raises(ValueError, match="mismatch"):
        collector.check_archive(path, {"expected_hashes": {"sha256": "0" * 64}})
    path.write_bytes(b"<html>not an archive</html>")
    with pytest.raises(tarfile.ReadError):
        collector.check_archive(path, {})


def test_additional_source_zip_never_extracts_and_rejects_traversal(tmp_path, monkeypatch):
    import zipfile
    collector = packaging_module("collect_additional_sources", monkeypatch)
    path = tmp_path / "source.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../LICENSE", "untrusted")
    with pytest.raises(ValueError, match="Unsafe"):
        collector.check_archive(path, {})
    assert not (tmp_path.parent / "LICENSE").exists()


@pytest.mark.parametrize("name", ["LICENSE", "license.txt", "OFL.txt", "docs/FTL.TXT", "font_license.txt"])
def test_original_notice_filename_selection(name, monkeypatch):
    assert packaging_module("collect_source_notices", monkeypatch).is_notice(Path(name).name)


def test_source_notices_preserve_complete_inline_inchi_license(tmp_path, monkeypatch):
    collector = packaging_module("collect_source_notices", monkeypatch)
    path = tmp_path / "source.tar.xz"
    notice = "/* Copyright Example\n * Permission notice and disclaimer.\n */\n"
    qt_archive(path, {"inchi/src/example.c": notice + "int main() { return 0; }"})
    records = collector.extract_notices(path, "inchi", tmp_path / "notices")
    assert len(records) == 1
    assert (tmp_path / "notices/inchi/src/example.c.notice.txt").read_text() == notice


def test_source_notices_refuse_changed_output(tmp_path, monkeypatch):
    collector = packaging_module("collect_source_notices", monkeypatch)
    path = tmp_path / "source.tar.xz"
    qt_archive(path, {"source/LICENSE": "original"})
    output = tmp_path / "notices"
    collector.extract_notices(path, "component", output)
    (output / "component/LICENSE").write_text("user edit")
    with pytest.raises(ValueError, match="overwrite"):
        collector.extract_notices(path, "component", output)
    assert (output / "component/LICENSE").read_text() == "user edit"


@pytest.mark.parametrize("component", [".", ".."])
def test_source_notice_component_cannot_escape_destination(tmp_path, monkeypatch, component):
    with pytest.raises(ValueError, match="Unsafe component"):
        packaging_module("collect_source_notices", monkeypatch).extract_notices(
            tmp_path / "unopened.tar.gz", component, tmp_path / "notices")


def test_source_notices_reject_windows_path_and_case_collisions(tmp_path, monkeypatch):
    collector = packaging_module("collect_source_notices", monkeypatch)
    path = tmp_path / "source.tar.xz"
    qt_archive(path, {"source/C:/LICENSE": "bad"})
    with pytest.raises(ValueError, match="Unsafe"):
        collector.extract_notices(path, "component", tmp_path / "notices")
    qt_archive(path, {"source/LICENSE": "one", "source/license": "two"})
    with pytest.raises(ValueError, match="Duplicate"):
        collector.extract_notices(path, "component", tmp_path / "notices")


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


def source_package(path, content=b"source payload", *, extra=(), expected=None):
    checksum = expected or hashlib.sha256(content).hexdigest()
    metadata = ("pkgbase = example\n\tpkgver = 1.0\n\tpkgrel = 1\n"
                "\tsource = source.tar.gz::https://example.org/source\n"
                f"\tsha256sums = {checksum}\n")
    with tarfile.open(path, "w") as archive:
        for name, payload in [("example/.SRCINFO", metadata.encode()),
                              ("example/PKGBUILD", b"never execute this recipe"),
                              ("example/source.tar.gz", content), *extra]:
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))


def test_nested_source_hash_is_verified_without_execution(tmp_path):
    archive = tmp_path / "sources.tar"
    source_package(archive)
    result = module("verify_source_inputs").verify_package(archive, "example", "1.0-1")
    assert result["all_inputs_hash_verified"]
    assert result["inputs"][0]["verified_algorithms"] == ["sha256"]


def test_nested_source_hash_mismatch_fails(tmp_path):
    archive = tmp_path / "sources.tar"
    source_package(archive, expected="0" * 64)
    with pytest.raises(ValueError, match="sha256 mismatch"):
        module("verify_source_inputs").verify_package(archive, "example", "1.0-1")


def test_source_package_identity_is_verified(tmp_path):
    archive = tmp_path / "sources.tar"
    source_package(archive)
    with pytest.raises(ValueError, match="identity mismatch"):
        module("verify_source_inputs").verify_package(archive, "example", "2.0-1")


@pytest.mark.parametrize("name", ["../outside", "/outside", "example/../outside", "example\\outside"])
def test_source_hash_checker_rejects_unsafe_entries(tmp_path, name):
    archive = tmp_path / "sources.tar"
    source_package(archive, extra=[(name, b"invalid")])
    with pytest.raises(ValueError, match="Unsafe archive path"):
        module("verify_source_inputs").verify_package(archive, "example", "1.0-1")


def test_source_hash_checker_rejects_duplicate_entries(tmp_path):
    archive = tmp_path / "sources.tar"
    source_package(archive, extra=[("example/source.tar.gz", b"second payload")])
    with pytest.raises(ValueError, match="Duplicate source entry"):
        module("verify_source_inputs").verify_package(archive, "example", "1.0-1")


def test_source_hash_checker_rejects_symlinks(tmp_path):
    archive = tmp_path / "sources.tar"
    source_package(archive)
    with tarfile.open(archive, "a") as output:
        member = tarfile.TarInfo("example/link")
        member.type = tarfile.SYMTYPE
        member.linkname = "/outside"
        output.addfile(member)
    with pytest.raises(ValueError, match="non-file source entry"):
        module("verify_source_inputs").verify_package(archive, "example", "1.0-1")


def test_architecture_specific_inputs_keep_matching_checksums():
    checker = module("verify_source_inputs")
    fields = checker.fields_from_srcinfo("source_x86_64 = source.c\nsha256sums_x86_64 = abc\n")
    result = checker.verify_payload(fields, {"source.c": {"sha256": "abc"}}, {"source.c"})
    assert result[0]["status"] == "hash-verified"
    assert result[0]["group"] == "source_x86_64"


def test_source_checksum_count_must_match():
    with pytest.raises(ValueError, match="Checksum count"):
        module("verify_source_inputs").verify_payload(
            {"source": ["one", "two"], "sha256sums": ["abc"]}, {}, set())


def test_skip_and_vcs_are_never_claimed_hash_verified():
    checker = module("verify_source_inputs")
    fields = {"source": ["source.sig", "repo::git+https://example.org/repo#commit=" + "a" * 40],
              "sha256sums": ["SKIP", "a" * 64]}
    results = checker.verify_payload(fields, {"source.sig": {"sha256": "abc"}},
                                     {"source.sig", "repo/objects/pack/example.pack"})
    assert [r["status"] for r in results] == ["present-not-hash-verified",
                                             "vcs-payload-present-not-verified"]


def test_missing_source_and_vcs_payload_fail():
    checker = module("verify_source_inputs")
    for source in ("missing", "repo::git+https://example.org/repo"):
        with pytest.raises(ValueError, match="Missing"):
            checker.verify_payload({"source": [source]}, {}, set())


@pytest.mark.parametrize("source", ["../file::https://example.org/a", "..::https://example.org/a",
                                     "x\\y::https://example.org/a"])
def test_source_alias_cannot_escape_package(source):
    with pytest.raises(ValueError, match="Unsafe source filename"):
        module("verify_source_inputs").source_filename(source)
