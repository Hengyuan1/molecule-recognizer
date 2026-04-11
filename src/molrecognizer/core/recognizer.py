"""MolScribe-based molecular structure recognizer with model caching."""

from __future__ import annotations

import os
import tempfile
import warnings
from pathlib import Path
from typing import Optional, Union

import numpy as np
import torch
from PIL import Image
from rdkit import Chem
from rdkit.Chem import AllChem

from .molecule import BondType, Molecule

# Suppress HuggingFace warnings
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Singleton model cache (keyed by device string)
_model_cache: dict[str, "MoleculeRecognizer"] = {}


class MoleculeRecognizer:
    """Recognizes molecular structures from images using MolScribe.

    The model is loaded once and cached globally — subsequent calls to
    ``MoleculeRecognizer()`` with the same device reuse the same model.

    Usage:
        recognizer = MoleculeRecognizer()
        mol = recognizer.recognize("molecule.png")
    """

    def __new__(cls, device: Optional[str] = None) -> "MoleculeRecognizer":
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        if device in _model_cache:
            return _model_cache[device]
        instance = super().__new__(cls)
        instance._initialized = False
        return instance

    def __init__(self, device: Optional[str] = None) -> None:
        if self._initialized:
            return
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self._device_str = device
        self._device = torch.device(device)

        from huggingface_hub import hf_hub_download
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ckpt_path = hf_hub_download("yujieq/MolScribe", "swin_base_char_aux_1m.pth")

        from molscribe import MolScribe
        self._model = MolScribe(ckpt_path, device=self._device)
        self._initialized = True
        _model_cache[device] = self

    def recognize(self, image: Union[str, Path, Image.Image, np.ndarray]) -> Molecule:
        """Recognize a molecular structure from an image.

        Prefers the SMILES string from MolScribe (preserves bond types),
        then falls back to building from atom/bond coordinate data.
        """
        if isinstance(image, np.ndarray):
            img = Image.fromarray(image)
            return self._recognize_pil(img)
        elif isinstance(image, Image.Image):
            return self._recognize_pil(image)
        else:
            return self._recognize_file(str(image))

    def recognize_to_smiles(self, image: Union[str, Path, Image.Image, np.ndarray]) -> str:
        """Recognize a molecular structure and return its SMILES string."""
        from .smiles import molecule_to_smiles
        mol = self.recognize(image)
        return molecule_to_smiles(mol)

    def _recognize_file(self, path: str) -> Molecule:
        output = self._model.predict_image_file(
            path, return_atoms_bonds=True, return_confidence=True
        )
        return self._output_to_molecule(output)

    def _recognize_pil(self, img: Image.Image) -> Molecule:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as f:
            img.save(f, format="PNG")
            f.flush()
            return self._recognize_file(f.name)

    def _output_to_molecule(self, output: dict) -> Molecule:
        """Convert MolScribe output to a Molecule.

        Strategy: prefer SMILES (preserves aromaticity and bond orders),
        fall back to atom/bond graph construction.
        """
        smiles = output.get("smiles", "")

        # Try SMILES first — it preserves double bonds, aromaticity, etc.
        if smiles:
            try:
                rdmol = Chem.MolFromSmiles(smiles)
                if rdmol is not None:
                    rdmol = Chem.RemoveHs(rdmol)
                    AllChem.Compute2DCoords(rdmol)
                    return Molecule.from_rdkit(rdmol)
            except Exception:
                pass

        # Fallback: build from atom/bond data
        atoms = output.get("atoms", [])
        bonds = output.get("bonds", [])
        if atoms and bonds:
            return self._build_from_atoms_bonds(atoms, bonds)

        raise ValueError("MolScribe returned no usable output")

    def _build_from_atoms_bonds(self, atoms: list[dict], bonds: list[dict]) -> Molecule:
        """Build a Molecule from MolScribe's atom/bond dictionaries."""
        # MolScribe returns bond_type as strings ("single", "double", "triple")
        # or integers (1, 2, 3) depending on version.
        _bond_map = {
            "single": BondType.SINGLE, 1: BondType.SINGLE,
            "double": BondType.DOUBLE, 2: BondType.DOUBLE,
            "triple": BondType.TRIPLE, 3: BondType.TRIPLE,
            "aromatic": BondType.AROMATIC,
        }
        mol = Molecule()
        for atom_data in atoms:
            element = atom_data.get("atom_symbol", "C")
            x = atom_data.get("x", 0.0) * 10.0
            y = atom_data.get("y", 0.0) * 10.0
            charge = atom_data.get("charge", 0)
            mol.add_atom(element, x, y, formal_charge=charge)
        for bond_data in bonds:
            endpoints = bond_data.get("endpoint_atoms", [0, 1])
            if len(endpoints) < 2:
                continue
            idx1, idx2 = endpoints[0], endpoints[1]
            if idx1 >= mol.num_atoms or idx2 >= mol.num_atoms:
                continue
            raw_type = bond_data.get("bond_type", "single")
            bt = _bond_map.get(raw_type, BondType.SINGLE)
            mol.add_bond(idx1, idx2, bt)
        return mol
