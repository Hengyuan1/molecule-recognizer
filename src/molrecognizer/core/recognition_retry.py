"""Explicit, bounded OSRA alternatives. Never select a winner automatically."""

from dataclasses import dataclass
import math
from pathlib import Path
import tempfile

from PIL import Image, ImageOps

from .molecule import Molecule
from .layout import straighten_terminal_nitriles
from .recognizer import OSRARecognizer, RecognitionCancelled


@dataclass(frozen=True)
class RetryProfile:
    name: str
    options: tuple[str, ...]
    description: str
    scale: int = 1


RETRY_PROFILES = (
    RetryProfile("Adaptive threshold", ("-i",),
                 "Use adaptive thresholding with a white margin to reduce false border bonds."),
    RetryProfile("100 dpi interpretation", ("-r", "100"),
                 "Interpret the existing pixels as 100 dpi; this does not add image detail."),
    RetryProfile("Threshold 0.35", ("-t", "0.35"),
                 "Use a different grayscale cutoff for detecting lines and labels."),
    RetryProfile("2x enlarged", (),
                 "Enlarge an OCR-only copy 2x with a white margin; source pixels are not changed.", 2),
    RetryProfile("4x enlarged", (),
                 "Enlarge an OCR-only copy 4x with a white margin; this cannot recover missing detail.", 4),
)


@dataclass(frozen=True)
class RecognitionCandidate:
    name: str
    molecule: Molecule | None = None
    confidence: float | None = None
    error: str = ""


def _adaptive_retry_image(image: Image.Image, scale: int = 1) -> Image.Image:
    """Give OSRA a white margin, optionally enlarging an OCR-only copy.

    On tightly cropped inputs, native Windows OSRA's adaptive thresholding can
    interpret the image boundary as bonds, even attaching them to the molecule.
    Pad the raster input instead of trying to remove bonds from its output.
    Composite transparency onto white so hidden dark pixels cannot form a frame.
    The default scale preserves every source pixel; only explicit enlarged
    profiles resample. Neither path modifies the original image.
    """
    if scale != 1 and (image.width * image.height * scale * scale > 8_000_000
                       or max(image.size) * scale > 8000):
        raise ValueError("Enlarged retry exceeds the size limit; use a tighter crop instead.")
    rgba = image.convert("RGBA")
    opaque = Image.new("RGB", image.size, "white")
    opaque.paste(rgba, mask=rgba.getchannel("A"))
    if scale != 1:
        opaque = opaque.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)
    return ImageOps.expand(opaque, border=24, fill="white")


def recognition_alternatives(image: Image.Image, recognizer: OSRARecognizer,
                             on_status=None):
    """Yield one result per preset, retaining SDF drawing/stereo information.

    One temporary PNG path is reused and removed on success, failure or
    cancellation. Adaptive and explicitly enlarged attempts get a white margin;
    threshold/DPI presets get the original image. The source is never modified. Each attempt
    gets at most 15 seconds of OSRA processing plus the normal 10-second
    subprocess grace period.
    """
    recognizer._check_cancelled()
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            path = Path(temp.name)
        for index, profile in enumerate(RETRY_PROFILES, 1):
            recognizer._check_cancelled()
            if on_status is not None:
                on_status(f"Trying {profile.name} ({index}/{len(RETRY_PROFILES)})…")
            try:
                prepared = (_adaptive_retry_image(image, profile.scale)
                            if "-i" in profile.options or profile.scale != 1 else image)
                prepared.save(path, format="PNG")
                recognizer._check_cancelled()
                rd = recognizer._read_sdf(
                    path, timeout=min(recognizer.timeout, 15),
                    options=(*profile.options, "-p"))
                if rd is None:
                    raise ValueError("No usable structure returned")
                confidence = None
                if rd.HasProp("Confidence_estimate"):
                    try:
                        score = float(rd.GetProp("Confidence_estimate"))
                        if math.isfinite(score):
                            confidence = score
                    except ValueError:
                        pass
                candidate = RecognitionCandidate(
                    profile.name, Molecule.from_rdkit(straighten_terminal_nitriles(rd)), confidence)
            except RecognitionCancelled:
                raise
            except Exception as error:
                candidate = RecognitionCandidate(profile.name, error=str(error))
            recognizer._check_cancelled()
            yield candidate
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
