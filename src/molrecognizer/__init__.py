"""Molecule Recognizer — recognize molecular structures from images.

Public API:
    recognize(image_path) → SMILES string
    smiles_to_molecule(smiles) → Molecule
    molecule_to_smiles(mol) → str
    check_valence(mol) → list[ValenceWarning]
    Molecule — editable molecule with 2D coordinates
    MoleculeRecognizer — OSRA-based recognizer class (MolScribe optional)
"""

from molrecognizer.core.molecule import BondType, Molecule
from molrecognizer.core.smiles import molecule_to_smiles, smiles_to_molecule
from molrecognizer.core.valence import ValenceWarning, check_valence


def recognize(
    image_path: str,
    device: str = "cpu",
    backend: str = "osra",
) -> str:
    """Recognize a molecular structure from an image file and return its SMILES string.

    Args:
        image_path: Path to a molecule image (PNG, JPG, etc.).
        device: PyTorch device when ``backend="molscribe"``.
        backend: Recognition backend, ``"osra"`` (default) or ``"molscribe"``.

    Returns:
        Canonical SMILES string of the recognized molecule.

    Example:
        >>> import molrecognizer
        >>> smiles = molrecognizer.recognize("molecule.png")
        >>> print(smiles)
        'c1ccccc1'
    """
    from molrecognizer.core.recognizer import MoleculeRecognizer
    recognizer = MoleculeRecognizer(device=device, backend=backend)
    return recognizer.recognize_to_smiles(image_path)


def recognize_to_molecule(
    image_path: str,
    device: str = "cpu",
    backend: str = "osra",
) -> Molecule:
    """Recognize a molecular structure from an image file and return a Molecule.

    Args:
        image_path: Path to a molecule image (PNG, JPG, etc.).
        device: PyTorch device when ``backend="molscribe"``.
        backend: Recognition backend, ``"osra"`` (default) or ``"molscribe"``.

    Returns:
        Molecule object with atoms, bonds, and 2D coordinates.
    """
    from molrecognizer.core.recognizer import MoleculeRecognizer
    recognizer = MoleculeRecognizer(device=device, backend=backend)
    return recognizer.recognize(image_path)


__all__ = [
    "recognize",
    "recognize_to_molecule",
    "molecule_to_smiles",
    "smiles_to_molecule",
    "check_valence",
    "Molecule",
    "BondType",
    "ValenceWarning",
]
