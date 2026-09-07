"""OSRA runtime collection tests, without requiring a Windows compiler."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def stager(monkeypatch):
    directory = Path(__file__).resolve().parents[1] / "packaging/windows"
    monkeypatch.syspath_prepend(str(directory))
    spec = importlib.util.spec_from_file_location("osra_stager_test", directory / "stage_osra.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dependency_closure_includes_plugins_and_cycles(stager, tmp_path, monkeypatch):
    source = tmp_path / "ucrt64/bin"
    source.mkdir(parents=True)
    output = tmp_path / "output"
    output.mkdir()
    system = tmp_path / "System32"
    system.mkdir()
    (system / "kernel32.dll").touch()
    for name in ("first.dll", "second.dll", "codec.dll"):
        (source / name).write_bytes(name.encode())
    imports = {"osra.exe": {"first.dll", "kernel32.dll"},
               "png.dll": {"codec.dll"}, "first.dll": {"second.dll"},
               "second.dll": {"first.dll", "api-ms-win-crt-runtime-l1-1-0.dll"},
               "codec.dll": {"second.dll"}}
    monkeypatch.setattr(stager, "imported_libraries", lambda path: imports[path.name])
    copied = stager.collect_dependencies([tmp_path / "osra.exe", tmp_path / "png.dll"],
                                         [source], output, system)
    assert {path.name for path in copied} == {"first.dll", "second.dll", "codec.dll"}
    assert {path.name for path in output.iterdir()} == {path.name for path in copied}


@pytest.mark.parametrize("dependency", ["missing.dll", "msys-2.0.dll", "cygwin1.dll"])
def test_rejects_unresolved_or_unix_runtime_dependency(stager, tmp_path, monkeypatch, dependency):
    monkeypatch.setattr(stager, "imported_libraries", lambda path: {dependency})
    with pytest.raises(RuntimeError, match="dependency"):
        stager.collect_dependencies([tmp_path / "osra.exe"], [], tmp_path, tmp_path / "System32")


def test_stage_never_overwrites_a_runtime(stager, tmp_path):
    with pytest.raises(FileExistsError, match="overwrite"):
        stager.stage(tmp_path / "msys64", tmp_path)


def test_package_provenance_requires_exact_ownership(stager, tmp_path):
    package = tmp_path / "var/lib/pacman/local/example-1.2.3-1"
    package.mkdir(parents=True)
    (package / "files").write_text("%FILES%\nucrt64/bin/example.dll\n", encoding="utf-8")
    (package / "desc").write_text(
        "%NAME%\nexample\n\n%VERSION%\n1.2.3-1\n\n%BASE%\nmingw-w64-example\n"
        "\n%LICENSE%\nMIT\n\n%URL%\nhttps://example.org\n", encoding="utf-8")
    result = stager.package_provenance(tmp_path, [tmp_path / "ucrt64/bin/example.dll"])
    assert result[0]["name"] == ["example"]
    assert result[0]["version"] == ["1.2.3-1"]
    assert result[0]["files"] == ["ucrt64/bin/example.dll"]
    with pytest.raises(RuntimeError, match="provenance"):
        stager.package_provenance(tmp_path, [tmp_path / "ucrt64/bin/unknown.dll"])
