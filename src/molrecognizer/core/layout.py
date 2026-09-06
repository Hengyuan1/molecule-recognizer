"""Stereo-safe 2D layout cleanup."""

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem

from .molecule import Molecule
from .smiles import molecule_to_smiles
from .stereo import with_drawing_stereo


def format_2d(mol: Molecule) -> Molecule:
    """Return a clean drawing, preserving chemistry and approximate orientation.

    Wedges describe chirality relative to the surrounding coordinates. Moving
    atoms without recalculating wedges can invert a stereocenter. Perceive the
    old drawing first, lay out a copy, then re-wedge for the new coordinates.
    """
    original = mol.to_rdkit()
    if mol.num_atoms == 0:
        result = Molecule()
        result._mol = Chem.RWMol(original)
        return result
    drawing = with_drawing_stereo(original)
    before_smiles = molecule_to_smiles(mol)
    old_positions = np.asarray(mol.get_2d_coords())
    AllChem.Compute2DCoords(drawing)
    conf = drawing.GetConformer()
    positions = np.asarray(conf.GetPositions())[:, :2]

    # Fit the cleaned layout back onto the old drawing. Reflection is allowed
    # here to undo the layout engine's arbitrary mirror choice; wedging below
    # is derived from the saved stereo tags *after* this alignment.
    old_center = old_positions.mean(axis=0)
    center = positions.mean(axis=0)
    u, _, vt = np.linalg.svd((positions - center).T @ (old_positions - old_center))
    positions = (positions - center) @ (u @ vt) + old_center
    for idx, (x, y) in enumerate(positions):
        conf.SetAtomPosition(idx, (float(x), float(y), 0.0))

    stereo_dirs = (Chem.BondDir.BEGINWEDGE, Chem.BondDir.BEGINDASH)
    tetrahedral = (Chem.ChiralType.CHI_TETRAHEDRAL_CW, Chem.ChiralType.CHI_TETRAHEDRAL_CCW)
    for bond in drawing.GetBonds():
        if bond.GetBondDir() in stereo_dirs:
            bond.SetBondDir(Chem.BondDir.NONE)
        # These markings belong to the original imported coordinates.
        for prop in ('_MolFileBondStereo', '_MolFileBondCfg'):
            if bond.HasProp(prop):
                bond.ClearProp(prop)
    for original_bond in original.GetBonds():
        if original_bond.GetBondDir() not in stereo_dirs:
            continue
        bond = drawing.GetBondWithIdx(original_bond.GetIdx())
        begin = original_bond.GetBeginAtomIdx()
        if drawing.GetAtomWithIdx(begin).GetChiralTag() in tetrahedral:
            # Keep the user's chosen bond and its narrow endpoint.
            Chem.WedgeBond(bond, begin, conf)
        else:
            # A manually drawn marking on a non-stereocenter has no absolute
            # configuration to preserve, but shouldn't silently disappear.
            bond.SetBondDir(original_bond.GetBondDir())
    Chem.WedgeMolBonds(drawing, conf)
    for atom, old_atom in zip(drawing.GetAtoms(), original.GetAtoms()):
        atom.SetNoImplicit(old_atom.GetNoImplicit())

    result = Molecule()
    result._mol = drawing
    if molecule_to_smiles(result) != before_smiles:
        raise ValueError("Layout cleanup could not preserve stereochemistry; the original drawing was kept.")
    return result
