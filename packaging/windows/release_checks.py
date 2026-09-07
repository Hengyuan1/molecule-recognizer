"""Small deterministic release checks shared by the builder and tests."""

from pathlib import PurePosixPath


# Qt's generic hooks collect plugins we never use. Virtual Keyboard is a
# GPL-only add-on; it also pulls in QML/Quick. Qt PDF pulls in Chromium code.
# Our 2D and 3D views both use QWidget/QPainter, not OpenGL or QML.
UNUSED_QT_BINARIES = frozenset({
    "qtvirtualkeyboardplugin.dll", "qt6virtualkeyboard.dll", "qpdf.dll", "qt6pdf.dll",
    "qt6qml.dll", "qt6qmlmeta.dll", "qt6qmlmodels.dll", "qt6qmlworkerscript.dll",
    "qt6quick.dll", "opengl32sw.dll",
})


def include_binary(destination):
    path = PurePosixPath(str(destination).replace("\\", "/"))
    return not ("pyside6" in {part.lower() for part in path.parts}
                and path.name.lower() in UNUSED_QT_BINARIES)


def require_source_revision(revision):
    import re
    if revision is not None and not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("--source-revision must be a full, lowercase Git commit hash")
    return revision


def validate_qt_payload(bundle):
    qt = bundle / "_internal/PySide6"
    unexpected = sorted(str(path.relative_to(bundle)) for path in qt.rglob("*")
                        if path.is_file() and not include_binary(path.relative_to(bundle)))
    if unexpected:
        raise ValueError(f"Unneeded Qt components in release payload: {unexpected}")
    for relative in ("Qt6Core.dll", "Qt6Gui.dll", "Qt6Widgets.dll", "Qt6Svg.dll",
                     "plugins/platforms/qwindows.dll", "plugins/platforms/qoffscreen.dll",
                     "plugins/iconengines/qsvgicon.dll"):
        if not (qt / relative).is_file():
            raise ValueError(f"Missing required Qt runtime: {relative}")
