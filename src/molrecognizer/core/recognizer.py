"""MolScribe-based molecular structure recognizer."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional, Union

import numpy as np
import torch
from huggingface_hub import hf_hub_download
from molscribe import MolScribe
from PIL import Image
from rdkit import Chem
from rdkit.Chem import AllChem

from .molecule import BondType, Molecule

# Map MolScribe bond type integers to our BondType enum
_MOLSCRIBE_BOND_MAP = {
    1: BondType.SINGLE,
    2: BondType.DOUBLE,
    3: BondType.TRIPLE,
}


class MoleculeRecognizer:
    """Recognizes molecular structures from images using MolScribe.

    Usage:
        recognizer = MoleculeRecognizer()
        mol = recognizer.recognize("molecule.png")
    """

    def __init__(self, device: Optional[str] = None) -> None:
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self._device = torch.device(device)
        ckpt_path = hf_hub_download("yujieq/MolScribe", "swin_base_char_aux_1m.pth")
        self._model = MolScribe(ckpt_path, device=self._device)

    def recognize(self, image: Union[str, Path, Image.Image, np.ndarray]) -> Molecule:
        """Recognize a molecular structure from an image.

        Args:
            image: File path, PIL Image, or numpy array of the molecule image.

        Returns:
            Molecule with atoms, bonds, and 2D coordinates.
        """
        # Normalize input to a file path (MolScribe's primary interface)
        if isinstance(image, np.ndarray):
            img = Image.fromarray(image)
            return self._recognize_pil(img)
        elif isinstance(image, Image.Image):
            return self._recognize_pil(image)
        else:
            return self._recognize_file(str(image))

    def recognize_to_smiles(self, image: Union[str, Path, Image.Image, np.ndarray]) -> str:
        """Recognize a molecular structure and return its SMILES string.

        This is a convenience method that combines recognition + SMILES export.
        """
        from .smiles import molecule_to_smiles
        mol = self.recognize(image)
        return molecule_to_smiles(mol)

    def _recognize_file(self, path: str) -> Molecule:
        output = self._model.predict_image_file(
            path, return_atoms_bonds=True, return_confidence=True
        )
        return self._output_to_molecule(output)

    def _recognize_pil(self, img: Image.Image) -> Molecule:
        # MolScribe expects a file path; write to a temp file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as f:
            img.save(f, format="PNG")
            f.flush()
            return self._recognize_file(f.name)

    def _output_to_molecule(self, output: dict) -> Molecule:
        """Convert MolScribe output dict to a Molecule.

        MolScribe returns atoms and bonds when return_atoms_bonds=True.
        Falls back to SMILES parsing if atom/bond data is missing.
        """
        atoms = output.get("atoms", [])
        bonds = output.get("bonds", [])

        # If we have atom/bond data, build the molecule from it
        if atoms and bonds:
            return self._build_from_atoms_bonds(atoms, bonds)

        # Fallback: parse the SMILES string
        smiles = output.get("smiles", "")
        if smiles:
            from .smiles import smiles_to_molecule
            return smiles_to_molecule(smiles)

        raise ValueError("MolScribe returned no usable output")

    def _build_from_atoms_bonds(self, atoms: list[dict], bonds: list[dict]) -> Molecule:
        """Build a Molecule from MolScribe's atom/bond dictionaries."""
        mol = Molecule()

        # Add atoms with their detected positions
        for atom_data in atoms:
            element = atom_data.get("atom_symbol", "C")
            # MolScribe gives normalized coordinates [0,1] — scale to reasonable coords
            x = atom_data.get("x", 0.0) * 10.0
            y = atom_data.get("y", 0.0) * 10.0
            charge = atom_data.get("charge", 0)
            mol.add_atom(element, x, y, formal_charge=charge)

        # Add bonds
        for bond_data in bonds:
            a1 = bond_data.get("endpoint_atoms", [0, 1])
            if len(a1) < 2:
                continue
            idx1, idx2 = a1[0], a1[1]
            if idx1 >= mol.num_atoms or idx2 >= mol.num_atoms:
                continue
            bond_order = bond_data.get("bond_type", 1)
            bt = _MOLSCRIBE_BOND_MAP.get(bond_order, BondType.SINGLE)
            mol.add_bond(idx1, idx2, bt)

        return mol
