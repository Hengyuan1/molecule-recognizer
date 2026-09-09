"""Release material integrity and provenance; no network or native build."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def materials(monkeypatch):
    directory = Path(__file__).resolve().parents[1] / "packaging/windows"
    monkeypatch.syspath_prepend(str(directory))
    spec = importlib.util.spec_from_file_location("release_materials", directory / "release_materials.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


@pytest.mark.parametrize("name", ["", ".", "../secret", "/secret", "C:/secret", "x:secret",
                                  "x\\secret", "./LICENSE", "a//LICENSE"])
def test_material_paths_are_portable_and_contained(tmp_path, materials, name):
    with pytest.raises(ValueError, match="Unsafe"):
        materials.safe_path(tmp_path, name)


def sealed_tree(path, materials):
    path.mkdir()
    (path / "LICENSE").write_text("Original notice", encoding="utf-8")
    manifest = {"schema": 1, "packages": {"Qt": "1.0"}, "files": materials.tree_files(path)}
    (path / "MATERIALS.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def test_material_integrity_and_version_match(tmp_path, materials):
    path = tmp_path / "notices"
    expected = sealed_tree(path, materials)
    assert materials.verify_materials(path, {"Qt": "1.0"}) == expected
    with pytest.raises(ValueError, match="not 2.0"):
        materials.verify_materials(path, {"Qt": "2.0"})


@pytest.mark.parametrize("change", ["edit", "remove", "extra"])
def test_material_changes_fail_closed(tmp_path, materials, change):
    path = tmp_path / "notices"
    sealed_tree(path, materials)
    if change == "edit":
        (path / "LICENSE").write_text("changed", encoding="utf-8")
    elif change == "remove":
        (path / "LICENSE").unlink()
    else:
        (path / "private.txt").write_text("must not enter archive", encoding="utf-8")
    with pytest.raises(ValueError, match="changed, missing, or contain unlisted"):
        materials.verify_materials(path)


def notice_fixture(tmp_path):
    directory = tmp_path / "notices"
    (directory / "component").mkdir(parents=True)
    payload = b"Original\r\nlicense notice\r\n"
    (directory / "component/LICENSE").write_bytes(payload)
    sources = [{"archive": "source.tar.gz", "component": "component", "sha256": "a" * 64}]
    component = {"archive": "source.tar.gz", "component": "component", "source_sha256": "a" * 64,
                 "notices": [{"file": "component/LICENSE", "sha256": hashlib.sha256(payload).hexdigest(),
                              "bytes": len(payload)}]}
    return directory, payload, sources, component


def test_only_inventoried_notices_are_copied_byte_for_byte(tmp_path, materials):
    directory, payload, sources, component = notice_fixture(tmp_path)
    (directory / "private.txt").write_text("do not copy", encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"components": [component]}), encoding="utf-8")
    output = tmp_path / "output"
    assert materials.copy_wheel_notices(directory, report, sources, output) == 1
    assert (output / "component/LICENSE").read_bytes() == payload
    assert not (output / "private.txt").exists()


@pytest.mark.parametrize("change", ["source_hash", "component", "notice_hash", "size", "duplicate", "traversal"])
def test_notice_provenance_tampering_is_rejected(tmp_path, materials, change):
    directory, _, sources, component = notice_fixture(tmp_path)
    if change == "source_hash":
        component["source_sha256"] = "b" * 64
    elif change == "component":
        component["component"] = "other"
    elif change == "notice_hash":
        component["notices"][0]["sha256"] = "b" * 64
    elif change == "size":
        component["notices"][0]["bytes"] += 1
    elif change == "duplicate":
        component["notices"] *= 2
    else:
        component["notices"][0]["file"] = "../LICENSE"
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"components": [component]}), encoding="utf-8")
    with pytest.raises(ValueError):
        materials.copy_wheel_notices(directory, report, sources, tmp_path / "output")


def test_bundled_license_help_uses_local_folder_without_network(tmp_path):
    from tests.test_shutdown import _run
    _run(tmp_path, '''
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PySide6.QtGui import QAction
actions = [action for action in window.findChildren(QAction)
           if action.text().startswith('Third-party licenses')]
assert len(actions) == 1
with TemporaryDirectory() as temporary:
    directory = Path(temporary) / 'licenses'
    directory.mkdir()
    with patch('molrecognizer.runtime.application_directory', return_value=Path(temporary)), \
         patch('molrecognizer.gui.main_window.QDesktopServices.openUrl', return_value=True) as opened:
        actions[0].trigger()
        url = opened.call_args.args[0]
        assert url.isLocalFile()
        assert Path(url.toLocalFile()) == directory
''')
