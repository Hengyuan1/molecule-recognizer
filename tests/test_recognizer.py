"""Tests for MolScribe-based recognizer.

These tests require MolScribe model weights (~400MB download on first run).
Mark with @pytest.mark.slow so they can be skipped in quick CI runs.
"""

import tempfile
from pathlib import Path

import pytest
from PIL import Image
from rdkit import Chem
from rdkit.Chem import AllChem, Draw


def _draw_molecule_to_file(smiles: str, path: str, size=(300, 300)):
    """Helper: draw a molecule from SMILES to a PNG file."""
    mol = Chem.MolFromSmiles(smiles)
    AllChem.Compute2DCoords(mol)
    img = Draw.MolToImage(mol, size=size)
    img.save(path)
    return path


@pytest.fixture(scope="module")
def recognizer():
    """Create recognizer once for all tests in this module (model loading is slow)."""
    from molrecognizer.core.recognizer import MoleculeRecognizer
    return MoleculeRecognizer(device="cpu")


@pytest.mark.slow
class TestRecognizer:
    def test_recognize_benzene(self, recognizer, tmp_path):
        img_path = str(tmp_path / "benzene.png")
        _draw_molecule_to_file("c1ccccc1", img_path)
        mol = recognizer.recognize(img_path)
        assert mol.num_atoms > 0
        assert mol.num_bonds > 0

    def test_recognize_ethanol(self, recognizer, tmp_path):
        img_path = str(tmp_path / "ethanol.png")
        _draw_molecule_to_file("CCO", img_path)
        mol = recognizer.recognize(img_path)
        assert mol.num_atoms > 0

    def test_recognize_pil_image(self, recognizer, tmp_path):
        img_path = str(tmp_path / "aspirin.png")
        _draw_molecule_to_file("CC(=O)Oc1ccccc1C(=O)O", img_path)
        img = Image.open(img_path)
        mol = recognizer.recognize(img)
        assert mol.num_atoms > 0

    def test_recognize_to_smiles(self, recognizer, tmp_path):
        img_path = str(tmp_path / "acetic.png")
        _draw_molecule_to_file("CC(=O)O", img_path)
        smiles = recognizer.recognize_to_smiles(img_path)
        assert isinstance(smiles, str)
        assert len(smiles) > 0
        # The returned SMILES should be valid
        mol = Chem.MolFromSmiles(smiles)
        assert mol is not None

    def test_recognize_numpy(self, recognizer, tmp_path):
        import numpy as np
        img_path = str(tmp_path / "methane.png")
        _draw_molecule_to_file("C", img_path, size=(200, 200))
        img = Image.open(img_path)
        arr = np.array(img)
        mol = recognizer.recognize(arr)
        assert mol.num_atoms > 0
