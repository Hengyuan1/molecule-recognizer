"""Export the approved vector app mark to transparent PNG and multi-size ICO.

Run with the project's Python on Windows or Linux. No image-generation call,
model, extra renderer or network access is needed for these format exports.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[2]
ICON_DIRECTORY = ROOT / "src/molrecognizer/gui/icons"
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def render(size: int) -> Image.Image:
    renderer = QSvgRenderer(str(ICON_DIRECTORY / "molrecognizer.svg"))
    if not renderer.isValid():
        raise ValueError("Invalid MolRecognizer SVG master")
    # Render each frame independently so small frames do not inherit a large
    # bitmap's antialiasing. Four-times supersampling smooths diagonal bonds.
    image = QImage(size * 4, size * 4, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, size * 4, size * 4))
    finally:
        painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError("Could not encode the icon")
    buffer.close()
    with Image.open(BytesIO(bytes(data))) as raster:
        return raster.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)


def main():
    frames = {size: render(size) for size in ICO_SIZES}
    destination = ICON_DIRECTORY / "molrecognizer.ico"
    frames[256].save(destination, format="ICO", sizes=[(size, size) for size in ICO_SIZES],
                     append_images=[frames[size] for size in ICO_SIZES if size != 256])
    render(1024).save(ICON_DIRECTORY / "molrecognizer.png")
    with Image.open(destination) as icon:
        assert icon.ico.sizes() == {(size, size) for size in ICO_SIZES}
        for size in ICO_SIZES:
            frame = icon.ico.getimage((size, size)).convert("RGBA")
            assert frame.getpixel((0, 0))[3] == 0
    print(f"Exported transparent PNG and ICO ({', '.join(map(str, ICO_SIZES))} px): {ICON_DIRECTORY}")


if __name__ == "__main__":
    main()
