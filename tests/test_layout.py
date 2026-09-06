"""Layout must never turn a drawing into a different stereoisomer."""

from unittest.mock import patch

import pytest
from rdkit import Chem
from rdkit.Chem import AllChem

from molrecognizer.core.layout import format_2d
from molrecognizer.core.molecule import Molecule
from molrecognizer.core.smiles import molecule_to_smiles, smiles_to_molecule
from molrecognizer.editor.history import FormatLayoutCommand, HistoryManager
from tests.test_history import _molecular_state
from tests.test_label_recovery import recovered_mol


@pytest.mark.parametrize('smiles', [
    'C[C@H](O)c1ccccc1', 'C[C@@H](O)c1ccccc1',
    'CC(C)[C@H]1CC[C@H](C)C[C@@H]1O', 'C[C@](O)(F)Cl',
    'C[C@H](O)[C@@H](N)C', 'F/C=C/F', 'F/C=C\\F', 'c1ccccc1', 'C',
])
def test_cleanup_preserves_chemical_identity(smiles):
    mol = smiles_to_molecule(smiles)
    state = _molecular_state(mol)
    result = format_2d(mol)
    assert molecule_to_smiles(result) == molecule_to_smiles(mol)
    assert _molecular_state(mol) == state  # No mutation until the command commits.


def test_cleanup_of_recognized_image_is_exactly_undoable():
    mol = Molecule.from_rdkit(recovered_mol())
    before = _molecular_state(mol)
    smiles = molecule_to_smiles(mol)
    history = HistoryManager(mol)
    history.execute(FormatLayoutCommand())
    after = _molecular_state(mol)
    assert before != after
    assert molecule_to_smiles(mol) == smiles
    for _ in range(3):
        history.undo()
        assert _molecular_state(mol) == before
        history.redo()
        assert _molecular_state(mol) == after
        assert molecule_to_smiles(mol) == smiles


def test_cleanup_rewedges_after_local_ligand_positions_change():
    mol = smiles_to_molecule('C[C@H](O)C(=O)O')
    # Test manually edited stereo as well: there are only directions, no tags.
    for atom in mol._mol.GetAtoms():
        atom.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
    expected = molecule_to_smiles(mol)
    compute = AllChem.Compute2DCoords
    def rearrange(rd):
        compute(rd)
        conf = rd.GetConformer()
        p0, p2 = conf.GetAtomPosition(0), conf.GetAtomPosition(2)
        conf.SetAtomPosition(0, p2)
        conf.SetAtomPosition(2, p0)
    with patch('molrecognizer.core.layout.AllChem.Compute2DCoords', side_effect=rearrange):
        result = format_2d(mol)
    assert molecule_to_smiles(result) == expected


def test_failed_cleanup_leaves_history_and_molecule_untouched():
    mol = Molecule.from_rdkit(recovered_mol())
    before = _molecular_state(mol)
    history = HistoryManager(mol)
    with patch('molrecognizer.core.layout.AllChem.Compute2DCoords', side_effect=ValueError('failed')):
        with pytest.raises(ValueError):
            history.execute(FormatLayoutCommand())
    assert _molecular_state(mol) == before
    assert not history.can_undo


def test_empty_cleanup_is_safe():
    assert format_2d(Molecule()).num_atoms == 0
