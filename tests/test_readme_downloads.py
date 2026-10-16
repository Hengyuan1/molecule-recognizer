"""Keep all current setup guides pointed at the same runnable Windows build."""

from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
READMES = ("README.md", "README.zh-CN.md", "README.ko.md", "README.ru.md", "README.fr.md")
RELEASES = "https://github.com/Hengyuan1/molecule-recognizer/releases"
TAG = "v0.3.0-main-canvas-fix.1"
BINARY = "MolRecognizer-0.3.0-main-canvas-fix-windows-x64.zip"
SOURCE = "MolRecognizer-0.3.0-main-canvas-fix-sources.zip"
DOWNLOAD = f"{RELEASES}/download/{TAG}/{BINARY}"


def links(text):
    return set(re.findall(r"\]\(([^\s)]+)\)", text))


@pytest.mark.parametrize("name", READMES)
def test_windows_header_steps_and_checksum_agree(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    urls = links(text)
    assert {url for url in urls if url.endswith("-windows-x64.zip")} == {DOWNLOAD}
    assert DOWNLOAD in "\n".join(text.splitlines()[:12])
    step = next(line for line in text.splitlines()
                if line.startswith("1. ") and "windows-x64.zip" in line)
    assert DOWNLOAD in step and "161" in step
    assert f"Get-FileHash .\\{BINARY} -Algorithm SHA256" in text
    assert f"Get-Content .\\{BINARY}.sha256" in text
    assert DOWNLOAD + ".sha256" in urls
    assert f"{RELEASES}/tag/{TAG}" in urls
    assert "pre-release" in text
    assert "MolRecognizer-0.3.0-windows-x64.zip" not in text


@pytest.mark.parametrize("name", READMES)
def test_application_sources_are_separate_from_base_dependency_sources(name):
    text = (ROOT / name).read_text(encoding="utf-8")
    urls = links(text)
    assert f"{RELEASES}/download/{TAG}/{SOURCE}" in urls
    assert f"{RELEASES}/download/v0.3.0/MolRecognizer-0.3.0-sources.zip" in urls
    guide = "packaging/windows/RELEASE-NOTES-main-canvas-fix.md"
    assert guide in urls and (ROOT / guide).is_file()
    assert "343a81b" in text and "MAIN-CANVAS-FIX.txt" in text


def test_packaging_guide_does_not_advertise_the_old_binary_as_current():
    text = (ROOT / "packaging/windows/README.md").read_text(encoding="utf-8")
    assert {url for url in links(text) if url.endswith("-windows-x64.zip")} == {DOWNLOAD}
    assert "No RC or v0.3.0 tag has been published" not in text
    assert "Historical release-candidate preparation" in text
