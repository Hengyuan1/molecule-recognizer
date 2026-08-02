"""Tests for the OSRA and MolScribe recognition backends.

These tests require MolScribe model weights (~400MB download on first run).
Mark with @pytest.mark.slow so they can be skipped in quick CI runs.
"""

from subprocess import CompletedProcess
from unittest.mock import patch

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
    return MoleculeRecognizer(device="cpu", backend="molscribe")


class TestOSRARecognizer:
    @patch("molrecognizer.core.recognizer.shutil.which", return_value="/usr/bin/osra")
    @patch("molrecognizer.core.recognizer.subprocess.run")
    def test_osra_sdf_preserves_coordinates_and_kekule_bonds(
        self, run, _which, tmp_path
    ):
        from molrecognizer.core.molecule import BondType
        from molrecognizer.core.recognizer import OSRARecognizer

        rwmol = Chem.RWMol()
        for _ in range(6):
            rwmol.AddAtom(Chem.Atom("C"))
        for begin, end, bond_type in (
            (0, 1, Chem.BondType.DOUBLE),
            (1, 2, Chem.BondType.SINGLE),
            (2, 3, Chem.BondType.DOUBLE),
            (3, 4, Chem.BondType.SINGLE),
            (4, 5, Chem.BondType.DOUBLE),
            (5, 0, Chem.BondType.SINGLE),
        ):
            rwmol.AddBond(begin, end, bond_type)
        conformer = Chem.Conformer(6)
        coordinates = [
            (0.2, 2.4), (1.8, 2.0), (2.3, 0.5),
            (1.1, -0.7), (-0.6, -0.2), (-1.0, 1.4),
        ]
        for index, (x, y) in enumerate(coordinates):
            conformer.SetAtomPosition(index, (x, y, 0.0))
        rwmol.AddConformer(conformer)
        sdf = Chem.MolToMolBlock(rwmol) + "\n$$$$\n"

        image_path = tmp_path / "ring.png"
        image_path.write_bytes(b"image")
        run.return_value = CompletedProcess([], 0, sdf.encode(), b"")

        molecule = OSRARecognizer().recognize(image_path)

        assert run.call_count == 1
        assert run.call_args.args[0][1:3] == ["-f", "sdf"]
        assert molecule.get_2d_coords() == pytest.approx(coordinates)
        bonds = molecule.get_all_bonds()
        assert bonds[0].bond_type == BondType.DOUBLE
        assert bonds[1].bond_type == BondType.SINGLE

    @patch("molrecognizer.core.recognizer.shutil.which", return_value="/usr/bin/osra")
    @patch("molrecognizer.core.recognizer.subprocess.run")
    def test_osra_is_default_and_returns_molecule(self, run, _which, tmp_path):
        from molrecognizer.core.recognizer import MoleculeRecognizer

        image_path = tmp_path / "structure.png"
        image_path.write_bytes(b"image")
        run.return_value = CompletedProcess([], 0, "CCO\n", "")

        recognizer = MoleculeRecognizer()
        molecule = recognizer.recognize(image_path)

        assert recognizer.backend_name == "OSRA"
        assert molecule.num_atoms == 3
        command = run.call_args.args[0]
        assert command[:3] == ["/usr/bin/osra", "-f", "can"]
        assert command[-1] == str(image_path)

    @patch("molrecognizer.core.recognizer.shutil.which", return_value="/usr/bin/osra")
    @patch("molrecognizer.core.recognizer.subprocess.run")
    def test_osra_uses_first_valid_output(self, run, _which, tmp_path):
        from molrecognizer.core.recognizer import OSRARecognizer

        image_path = tmp_path / "structures.png"
        image_path.write_bytes(b"image")
        run.return_value = CompletedProcess([], 0, "not_smiles\nc1ccccc1\nCCO\n", "")

        assert OSRARecognizer().recognize_to_smiles(image_path) == "c1ccccc1"

    @patch("molrecognizer.core.recognizer.shutil.which", return_value=None)
    def test_missing_osra_has_actionable_error(self, _which):
        from molrecognizer.core.recognizer import MoleculeRecognizer

        with pytest.raises(RuntimeError, match="OSRA_EXECUTABLE"):
            MoleculeRecognizer()

    @patch("molrecognizer.core.recognizer.shutil.which", return_value="/usr/bin/osra")
    @patch("molrecognizer.core.recognizer.subprocess.run")
    def test_osra_failure_includes_diagnostic(self, run, _which, tmp_path):
        from molrecognizer.core.recognizer import OSRARecognizer

        image_path = tmp_path / "structure.png"
        image_path.write_bytes(b"image")
        run.return_value = CompletedProcess([], 2, "", "cannot read image")

        with pytest.raises(RuntimeError, match="cannot read image"):
            OSRARecognizer().recognize(image_path)

    @patch("molrecognizer.core.recognizer.shutil.which", return_value="/usr/bin/osra")
    @patch("molrecognizer.core.recognizer.subprocess.run")
    def test_osra_accepts_valid_output_despite_nonzero_exit(
        self, run, _which, tmp_path
    ):
        from molrecognizer.core.recognizer import OSRARecognizer

        image_path = tmp_path / "structure.png"
        image_path.write_bytes(b"image")
        run.return_value = CompletedProcess([], 15, "CCO\n", "")

        assert OSRARecognizer().recognize_to_smiles(image_path) == "CCO"


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
