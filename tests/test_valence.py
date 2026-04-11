"""Tests for valence checking."""

from molrecognizer.core.molecule import BondType, Molecule
from molrecognizer.core.valence import check_valence


def _make_methane_skeleton():
    """CH4 skeleton: just C with 4 single bonds to H-placeholders (4 Hs as atoms)."""
    mol = Molecule()
    c = mol.add_atom("C", 0, 0)
    for i, (x, y) in enumerate([(1, 0), (-1, 0), (0, 1), (0, -1)]):
        h = mol.add_atom("H", x, y)
        mol.add_bond(c, h)
    return mol


def test_methane_valid():
    mol = _make_methane_skeleton()
    warnings = check_valence(mol)
    assert len(warnings) == 0


def test_carbon_five_bonds():
    """Carbon with 5 single bonds → valence violation."""
    mol = Molecule()
    c = mol.add_atom("C", 0, 0)
    for i in range(5):
        h = mol.add_atom("H", float(i), 1.0)
        mol.add_bond(c, h)
    warnings = check_valence(mol)
    carbon_warnings = [w for w in warnings if w.atom_index == 0]
    assert len(carbon_warnings) == 1
    assert carbon_warnings[0].actual_valence == 5


def test_nitrogen_three_bonds_valid():
    """N with 3 bonds (like NH3) should be valid."""
    mol = Molecule()
    n = mol.add_atom("N", 0, 0)
    for i in range(3):
        h = mol.add_atom("H", float(i), 1.0)
        mol.add_bond(n, h)
    warnings = check_valence(mol)
    n_warnings = [w for w in warnings if w.atom_index == 0]
    assert len(n_warnings) == 0


def test_nitrogen_four_bonds_invalid():
    """Neutral N with 4 bonds should warn (needs + charge to be valid)."""
    mol = Molecule()
    n = mol.add_atom("N", 0, 0)
    for i in range(4):
        h = mol.add_atom("H", float(i), 1.0)
        mol.add_bond(n, h)
    warnings = check_valence(mol)
    n_warnings = [w for w in warnings if w.atom_index == 0]
    assert len(n_warnings) == 1


def test_nitrogen_plus_four_bonds_valid():
    """N+ with 4 bonds (ammonium) should be valid."""
    mol = Molecule()
    n = mol.add_atom("N", 0, 0, formal_charge=1)
    for i in range(4):
        h = mol.add_atom("H", float(i), 1.0)
        mol.add_bond(n, h)
    warnings = check_valence(mol)
    n_warnings = [w for w in warnings if w.atom_index == 0]
    assert len(n_warnings) == 0


def test_oxygen_two_bonds_valid():
    mol = Molecule()
    o = mol.add_atom("O", 0, 0)
    h1 = mol.add_atom("H", 1, 0)
    h2 = mol.add_atom("H", -1, 0)
    mol.add_bond(o, h1)
    mol.add_bond(o, h2)
    warnings = check_valence(mol)
    o_warnings = [w for w in warnings if w.atom_index == 0]
    assert len(o_warnings) == 0


def test_oxygen_three_bonds_invalid():
    mol = Molecule()
    o = mol.add_atom("O", 0, 0)
    for i in range(3):
        h = mol.add_atom("H", float(i), 1.0)
        mol.add_bond(o, h)
    warnings = check_valence(mol)
    o_warnings = [w for w in warnings if w.atom_index == 0]
    assert len(o_warnings) == 1


def test_sulfur_multiple_valences():
    """S can have valence 2, 4, or 6."""
    # S with 2 bonds — valid
    mol = Molecule()
    s = mol.add_atom("S", 0, 0)
    for i in range(2):
        h = mol.add_atom("H", float(i), 1.0)
        mol.add_bond(s, h)
    assert len([w for w in check_valence(mol) if w.atom_index == 0]) == 0

    # S with 4 bonds — valid (like SO2 central S)
    mol2 = Molecule()
    s = mol2.add_atom("S", 0, 0)
    for i in range(4):
        o = mol2.add_atom("O", float(i), 1.0)
        mol2.add_bond(s, o)
    assert len([w for w in check_valence(mol2) if w.atom_index == 0]) == 0

    # S with 3 bonds — invalid
    mol3 = Molecule()
    s = mol3.add_atom("S", 0, 0)
    for i in range(3):
        h = mol3.add_atom("H", float(i), 1.0)
        mol3.add_bond(s, h)
    assert len([w for w in check_valence(mol3) if w.atom_index == 0]) == 1


def test_unknown_element_no_warning():
    """Elements not in the table should not produce warnings."""
    mol = Molecule()
    mol.add_atom("Fe", 0, 0)
    mol.add_atom("C", 1, 0)
    mol.add_bond(0, 1)
    warnings = check_valence(mol)
    fe_warnings = [w for w in warnings if w.element == "Fe"]
    assert len(fe_warnings) == 0


def test_ethanol_from_scratch():
    """Build ethanol (CCO) and verify no valence issues when correct."""
    mol = Molecule()
    c1 = mol.add_atom("C", 0, 0)
    c2 = mol.add_atom("C", 1.5, 0)
    o = mol.add_atom("O", 3.0, 0)
    h1 = mol.add_atom("H", -0.5, 0.8)
    h2 = mol.add_atom("H", -0.5, -0.8)
    h3 = mol.add_atom("H", 0.0, -1.0)
    h4 = mol.add_atom("H", 1.5, 0.8)
    h5 = mol.add_atom("H", 1.5, -0.8)
    h6 = mol.add_atom("H", 3.5, 0.5)
    mol.add_bond(c1, c2)
    mol.add_bond(c2, o)
    mol.add_bond(c1, h1)
    mol.add_bond(c1, h2)
    mol.add_bond(c1, h3)
    mol.add_bond(c2, h4)
    mol.add_bond(c2, h5)
    mol.add_bond(o, h6)
    warnings = check_valence(mol)
    assert len(warnings) == 0
