"""Local nitrile straightening must not regenerate the recognized drawing."""

from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image
from rdkit import Chem
from rdkit.Chem import AllChem

from molrecognizer.core.layout import straighten_terminal_nitriles
from molrecognizer.core.molecule import Molecule
from molrecognizer.core.recognition_retry import recognition_alternatives
from molrecognizer.core.recognizer import OSRARecognizer
from molrecognizer.core.smiles import molecule_to_smiles
from tests.test_history import _molecular_state


def bent_nitrile(smiles='C[C@H](O)c1ccc(C#N)cc1'):
    rd = Chem.MolFromSmiles(smiles)
    AllChem.Compute2DCoords(rd)
    Chem.WedgeMolBonds(rd, rd.GetConformer())
    anchor, carbon, nitrogen = rd.GetSubstructMatch(Chem.MolFromSmarts('[*]-[C]#[N]'))
    conf = rd.GetConformer()
    a, c = conf.GetAtomPosition(anchor), conf.GetAtomPosition(carbon)
    # Deliberately put C≡N perpendicular to the preceding bond.
    conf.SetAtomPosition(nitrogen, (c.x - (c.y - a.y), c.y + (c.x - a.x), 0))
    return rd, (anchor, carbon, nitrogen)


def assert_straight(rd, indices):
    a, c, n = rd.GetConformer().GetPositions()[list(indices), :2]
    first, last = c - a, n - c
    assert np.cross(first, last) == pytest.approx(0, abs=1e-9)
    assert np.dot(first, last) > 0  # N extends outward, not back over the ring.


@pytest.mark.parametrize('smiles', [
    'C[C@H](O)c1ccc(C#N)cc1', 'C[C@@H](O)C#N',
    'N#Cc1ccc(C#N)cc1', 'F/C=C/C#N', 'NC#N',
    'CC#[15N:7]',
])
def test_straightening_only_moves_terminal_nitrogen(smiles):
    source, indices = bent_nitrile(smiles)
    before = _molecular_state(Molecule.from_rdkit(source))
    result = straighten_terminal_nitriles(source)
    assert_straight(result, indices)
    before_positions = source.GetConformer().GetPositions()
    positions = result.GetConformer().GetPositions()
    anchor, carbon, nitrogen = indices
    assert np.linalg.norm(positions[nitrogen] - positions[carbon]) == pytest.approx(
        np.linalg.norm(before_positions[nitrogen] - before_positions[carbon]))
    for idx in range(source.GetNumAtoms()):
        if idx != nitrogen:
            assert positions[idx] == pytest.approx(before_positions[idx], abs=1e-12)
    after = _molecular_state(Molecule.from_rdkit(result))
    assert after[:2] == before[:2]  # Ordered atoms, bonds, stereo and metadata.
    assert molecule_to_smiles(Molecule.from_rdkit(result)) == molecule_to_smiles(Molecule.from_rdkit(source))
    assert _molecular_state(Molecule.from_rdkit(source)) == before
    assert np.allclose(straighten_terminal_nitriles(result).GetConformer().GetPositions(), positions)


@pytest.mark.parametrize('case', ['no_coords', '3d', 'zero_preceding', 'zero_triple',
                                 'charged_n', 'extra_n_bond', 'invalid_carbon'])
def test_ambiguous_or_degenerate_groups_are_unchanged(case):
    source, (a, c, n) = bent_nitrile()
    source = Chem.RWMol(source)
    conf = source.GetConformer()
    if case == 'no_coords':
        source.RemoveAllConformers()
    elif case == '3d':
        conf.Set3D(True)
    elif case == 'zero_preceding':
        conf.SetAtomPosition(c, conf.GetAtomPosition(a))
    elif case == 'zero_triple':
        conf.SetAtomPosition(n, conf.GetAtomPosition(c))
    elif case == 'charged_n':
        source.GetAtomWithIdx(n).SetFormalCharge(1)
    elif case == 'extra_n_bond':
        source.AddBond(n, a, Chem.BondType.SINGLE)
    elif case == 'invalid_carbon':
        source.GetBondBetweenAtoms(a, c).SetBondType(Chem.BondType.DOUBLE)
    before = source.ToBinary(Chem.PropertyPickleOptions.AllProps)
    result = straighten_terminal_nitriles(source)
    assert result.ToBinary(Chem.PropertyPickleOptions.AllProps) == before
    assert source.ToBinary(Chem.PropertyPickleOptions.AllProps) == before


def test_default_and_retry_import_use_identical_local_correction():
    source, indices = bent_nitrile()
    with patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra'):
        recognizer = OSRARecognizer()
    image = Image.new('RGB', (60, 40), 'white')
    with patch.object(recognizer, '_read_sdf', return_value=source):
        normal = recognizer.recognize(image)
        candidates = list(recognition_alternatives(image, recognizer))
    assert_straight(normal.to_rdkit(), indices)
    for candidate in candidates:
        assert not candidate.error
        assert _molecular_state(candidate.molecule) == _molecular_state(normal)
    a, c, n = source.GetConformer().GetPositions()[list(indices), :2]
    assert abs(np.cross(c - a, n - c)) > 0.1  # Raw SDF remains untouched.


@pytest.mark.parametrize('smiles', ['C[C@H](O)c1ccc(C#N)cc1', 'CC#CC'])
def test_format_of_unsanitized_sdf_keeps_triple_bonds_linear_and_undoable(smiles):
    from molrecognizer.editor.history import FormatLayoutCommand, HistoryManager

    source = Chem.MolFromSmiles(smiles)
    AllChem.Compute2DCoords(source)
    Chem.WedgeMolBonds(source, source.GetConformer())
    # Match the actual OSRA SDF import, not a sanitized SMILES-generated mol.
    raw = Chem.MolFromMolBlock(Chem.MolToMolBlock(source), sanitize=False, removeHs=False)
    Chem.ReapplyMolBlockWedging(raw)
    raw.UpdatePropertyCache(strict=False)
    assert all(a.GetHybridization() == Chem.HybridizationType.UNSPECIFIED for a in raw.GetAtoms())
    mol = Molecule.from_rdkit(raw)
    original = _molecular_state(mol)
    expected_smiles = molecule_to_smiles(mol)
    history = HistoryManager(mol)
    history.execute(FormatLayoutCommand())
    matches = raw.GetSubstructMatches(Chem.MolFromSmarts('[*]-[C]#[*]'), uniquify=False)
    assert matches
    for match in matches:
        assert_straight(mol.to_rdkit(), match)
    assert molecule_to_smiles(mol) == expected_smiles
    after = _molecular_state(mol)
    history.undo()
    assert _molecular_state(mol) == original
    history.redo()
    assert _molecular_state(mol) == after
