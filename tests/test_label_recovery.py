"""Conservative OCR label recovery without changing the original drawing."""

from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

import pytest
from PIL import Image
from rdkit import Chem

from molrecognizer.core.molecule import Molecule
from molrecognizer.core.recognizer import OSRARecognizer, _merge_label_retry
from molrecognizer.core.smiles import molecule_to_smiles

FIXTURE = Path(__file__).parent / 'data' / 'stereo_aliases.sdf'


def original_mol():
    mol = Chem.MolFromMolFile(str(FIXTURE), sanitize=False, removeHs=False)
    assert mol is not None
    mol.UpdatePropertyCache(strict=False)
    Chem.ReapplyMolBlockWedging(mol)
    return mol


def recovered_mol():
    mol = original_mol()
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 0:
            atom.SetAtomicNum(6)
            atom.ClearProp('molFileAlias')
    mol.UpdatePropertyCache(strict=False)
    return mol


def test_retry_merges_labels_with_different_atom_order_and_coordinates():
    original = original_mol()
    retry = Chem.RenumberAtoms(recovered_mol(), list(reversed(range(original.GetNumAtoms()))))
    conf = retry.GetConformer()
    for idx in range(retry.GetNumAtoms()):
        p = conf.GetAtomPosition(idx)
        conf.SetAtomPosition(idx, (p.x * 2 + 10, p.y * 2 - 20, 0))
    result = Molecule.from_rdkit(_merge_label_retry(original, retry))
    assert all(a.GetAtomicNum() != 0 for a in result._mol.GetAtoms())
    assert result.get_2d_coords() == Molecule.from_rdkit(original).get_2d_coords()
    assert result.get_all_bonds() == Molecule.from_rdkit(original).get_all_bonds()
    assert original.GetAtomWithIdx(7).GetAtomicNum() == 0
    assert original.GetAtomWithIdx(7).GetProp('molFileAlias') == 'CHS'
    assert Chem.MolToSmiles(Chem.MolFromSmiles(molecule_to_smiles(result))) == \
        'CC(C)[C@H]1CC[C@H](C)C[C@@H]1O'


@pytest.mark.parametrize('change', ['element', 'bond', 'stereo', 'charge', 'size'])
def test_retry_rejects_changed_known_structure(change):
    original = original_mol()
    retry = Chem.RWMol(recovered_mol())
    if change == 'element':
        retry.GetAtomWithIdx(8).SetAtomicNum(7)
    elif change == 'bond':
        retry.GetBondWithIdx(3).SetBondType(Chem.BondType.DOUBLE)
    elif change == 'stereo':
        retry.GetAtomWithIdx(0).InvertChirality()
    elif change == 'charge':
        retry.GetAtomWithIdx(8).SetFormalCharge(1)
    else:
        retry.AddAtom(Chem.Atom(6))
    assert _merge_label_retry(original, retry) is original


def test_ambiguous_mapping_does_not_guess_an_atom_identity():
    original = Chem.MolFromSmiles('*C*')
    for idx in [0, 2]:
        original.GetAtomWithIdx(idx).SetProp('molFileAlias', 'CHS')
    result = _merge_label_retry(original, Chem.MolFromSmiles('NCC'))
    assert result.GetAtomWithIdx(0).GetAtomicNum() == 0
    assert result.GetAtomWithIdx(2).GetAtomicNum() == 0


@pytest.mark.parametrize('label', ['', '*', 'R', 'R1', "R'", 'X', 'Ar'])
def test_intentional_placeholders_are_not_reinterpreted(label):
    original = Chem.MolFromSmiles('*C')
    original.GetAtomWithIdx(0).SetProp('molFileAlias', label)
    assert _merge_label_retry(original, Chem.MolFromSmiles('CC')) is original


@pytest.mark.parametrize('fails', [False, True])
@patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra')
def test_retry_is_bounded_and_temporary_image_is_removed(_which, tmp_path, fails):
    path = tmp_path / 'crop.png'
    Image.new('RGBA', (170, 230), (0, 0, 0, 0)).save(path)
    source_bytes = path.read_bytes()
    paths = []
    def run(command, **kwargs):
        paths.append(Path(command[-1]))
        if len(paths) == 1:
            return CompletedProcess([], 0, FIXTURE.read_bytes(), b'')
        assert len(paths) == 2
        assert command[command.index('--timeout') + 1] == '15'
        with Image.open(paths[-1]) as retry_image:
            assert retry_image.size == (380, 500)
            assert retry_image.getpixel((20, 20)) == (255, 255, 255)
        if fails:
            raise TimeoutExpired(command, 25)
        sdf = Chem.MolToMolBlock(recovered_mol()) + '\n$$$$\n'
        return CompletedProcess([], 0, sdf.encode(), b'')
    with patch('molrecognizer.core.recognizer.subprocess.run', side_effect=run):
        molecule = OSRARecognizer().recognize(path)
    assert len(paths) == 2 and not paths[-1].exists()
    assert path.read_bytes() == source_bytes
    assert sum(a.GetAtomicNum() == 0 for a in molecule._mol.GetAtoms()) == (2 if fails else 0)


@patch('molrecognizer.core.recognizer.shutil.which', return_value='/osra')
def test_large_image_does_not_trigger_upscale_retry(_which, tmp_path):
    path = tmp_path / 'large.png'
    Image.new('RGB', (1300, 100), 'white').save(path)
    with patch('molrecognizer.core.recognizer.subprocess.run',
               return_value=CompletedProcess([], 0, FIXTURE.read_bytes(), b'')) as run:
        OSRARecognizer().recognize(path)
    assert run.call_count == 1
