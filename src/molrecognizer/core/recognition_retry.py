"""Explicit, bounded OSRA alternatives. Never select a winner automatically."""

from dataclasses import dataclass
import math
from pathlib import Path
import tempfile

from PIL import Image

from .molecule import Molecule
from .layout import straighten_terminal_nitriles
from .recognizer import OSRARecognizer, RecognitionCancelled


@dataclass(frozen=True)
class RetryProfile:
    name: str
    options: tuple[str, ...]
    description: str


RETRY_PROFILES = (
    RetryProfile("Adaptive threshold", ("-i",),
                 "Separate text and bonds using adaptive thresholding."),
    RetryProfile("100 dpi interpretation", ("-r", "100"),
                 "Interpret the existing pixels as 100 dpi; this does not add image detail."),
    RetryProfile("Threshold 0.35", ("-t", "0.35"),
                 "Use a different grayscale cutoff for detecting lines and labels."),
)


@dataclass(frozen=True)
class RecognitionCandidate:
    name: str
    molecule: Molecule | None = None
    confidence: float | None = None
    error: str = ""


def recognition_alternatives(image: Image.Image, recognizer: OSRARecognizer,
                             on_status=None):
    """Yield one result per preset, retaining SDF drawing/stereo information.

    One full-resolution PNG is shared by the local attempts and removed on
    success, failure or cancellation. Each attempt gets at most 15 seconds of
    OSRA processing plus the normal 10-second subprocess grace period.
    """
    recognizer._check_cancelled()
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            path = Path(temp.name)
        image.save(path, format="PNG")
        for index, profile in enumerate(RETRY_PROFILES, 1):
            recognizer._check_cancelled()
            if on_status is not None:
                on_status(f"Trying {profile.name} ({index}/{len(RETRY_PROFILES)})…")
            try:
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
