"""Molecular structure recognition backends.

OSRA is the default backend and is invoked as a local command-line program.
MolScribe remains available as an explicit alternative.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import warnings
from pathlib import Path
from typing import Optional, Union

import numpy as np
from PIL import Image
from rdkit import Chem
from rdkit.Chem import AllChem

from .molecule import BondType, Molecule

ImageInput = Union[str, Path, Image.Image, np.ndarray]

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# MolScribe models are expensive to load, so cache them by device.
_model_cache: dict[str, "MolScribeRecognizer"] = {}


def _smiles_to_molecule(smiles: str, backend: str) -> Molecule:
    """Validate recognized SMILES and convert it to the editor model."""
    rdmol = Chem.MolFromSmiles(smiles)
    if rdmol is None:
        raise ValueError(f"{backend} returned invalid SMILES: {smiles!r}")
    rdmol = Chem.RemoveHs(rdmol)
    AllChem.Compute2DCoords(rdmol)
    try:
        Chem.WedgeMolBonds(rdmol, rdmol.GetConformer())
    except Exception:
        pass
    return Molecule.from_rdkit(rdmol)


class OSRARecognizer:
    """Recognize structures with a locally installed OSRA executable."""

    backend_name = "OSRA"

    def __init__(
        self,
        executable: Optional[Union[str, Path]] = None,
        timeout: int = 120,
    ) -> None:
        configured = executable or os.environ.get("OSRA_EXECUTABLE")
        resolved = shutil.which(str(configured)) if configured else shutil.which("osra")
        if resolved is None and configured is None:
            # Support a self-contained checkout/release without hard-coding
            # a user-specific path. DLLs can live next to osra.exe on Windows.
            project_root = Path(__file__).resolve().parents[3]
            names = ("osra.exe", "osra") if os.name == "nt" else ("osra", "osra.exe")
            for directory in (
                project_root / ".tools" / "osra" / "bin",
                project_root / "tools" / "osra" / "bin",
            ):
                for name in names:
                    candidate = directory / name
                    if candidate.is_file():
                        resolved = str(candidate)
                        break
                if resolved is not None:
                    break
        if resolved is None:
            raise RuntimeError(
                "OSRA is the default recognizer, but its executable was not found. "
                "Install OSRA on PATH, set OSRA_EXECUTABLE, place it under "
                ".tools/osra/bin, or use MoleculeRecognizer(backend='molscribe')."
            )
        self.executable = resolved
        self.timeout = timeout

    def recognize(self, image: ImageInput) -> Molecule:
        return _smiles_to_molecule(self.recognize_to_smiles(image), self.backend_name)

    def recognize_to_smiles(self, image: ImageInput) -> str:
        if isinstance(image, np.ndarray):
            return self._recognize_pil(Image.fromarray(image))
        if isinstance(image, Image.Image):
            return self._recognize_pil(image)
        return self._recognize_file(Path(image))

    def _recognize_pil(self, image: Image.Image) -> str:
        # Close the file before OSRA opens it, which is required on Windows.
        temp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
                temp_path = Path(temp.name)
            image.save(temp_path, format="PNG")
            return self._recognize_file(temp_path)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _recognize_file(self, path: Path) -> str:
        if not path.is_file():
            raise FileNotFoundError(f"Image file not found: {path}")
        command = [
            self.executable,
            "-f",
            "can",
            "--timeout",
            str(self.timeout),
            "--",
            str(path),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout + 10,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"OSRA recognition timed out after {self.timeout} seconds"
            ) from exc
        # OSRA prints one structure per line. This editor operates on one
        # molecule, so use the first valid structure in image-reading order.
        candidates = [line.strip().split()[0] for line in result.stdout.splitlines()
                      if line.strip()]
        for smiles in candidates:
            if Chem.MolFromSmiles(smiles) is not None:
                return smiles

        # Some OSRA builds return a nonzero status after successfully writing
        # a structure. Valid molecular output is therefore authoritative; a
        # nonzero code is only fatal when no usable SMILES was produced.
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(
                f"OSRA recognition failed (exit {result.returncode})"
                + (f": {detail}" if detail else "")
            )
        raise ValueError("OSRA found no usable molecular structure in the image")


class MolScribeRecognizer:
    """Recognize molecular structures using MolScribe."""

    backend_name = "MolScribe"

    def __new__(cls, device: Optional[str] = None) -> "MolScribeRecognizer":
        import torch

        selected = device or ("cuda" if torch.cuda.is_available() else "cpu")
        if selected in _model_cache:
            return _model_cache[selected]
        instance = super().__new__(cls)
        instance._initialized = False
        return instance

    def __init__(self, device: Optional[str] = None) -> None:
        if self._initialized:
            return
        import torch

        selected = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._device_str = selected
        self._device = torch.device(selected)

        from huggingface_hub import hf_hub_download
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            checkpoint = hf_hub_download(
                "yujieq/MolScribe", "swin_base_char_aux_1m.pth"
            )

        from molscribe import MolScribe
        self._model = MolScribe(checkpoint, device=self._device)
        self._initialized = True
        _model_cache[selected] = self

    def recognize(self, image: ImageInput) -> Molecule:
        if isinstance(image, np.ndarray):
            return self._recognize_pil(Image.fromarray(image))
        if isinstance(image, Image.Image):
            return self._recognize_pil(image)
        return self._recognize_file(str(image))

    def recognize_to_smiles(self, image: ImageInput) -> str:
        from .smiles import molecule_to_smiles
        return molecule_to_smiles(self.recognize(image))

    def _recognize_file(self, path: str) -> Molecule:
        output = self._model.predict_image_file(
            path, return_atoms_bonds=True, return_confidence=True
        )
        return self._output_to_molecule(output)

    def _recognize_pil(self, image: Image.Image) -> Molecule:
        with tempfile.NamedTemporaryFile(suffix=".png") as temp:
            image.save(temp, format="PNG")
            temp.flush()
            return self._recognize_file(temp.name)

    def _output_to_molecule(self, output: dict) -> Molecule:
        smiles = output.get("smiles", "")
        if smiles:
            try:
                return _smiles_to_molecule(smiles, self.backend_name)
            except ValueError:
                pass

        atoms = output.get("atoms", [])
        bonds = output.get("bonds", [])
        if atoms and bonds:
            return self._build_from_atoms_bonds(atoms, bonds)
        raise ValueError("MolScribe returned no usable output")

    def _build_from_atoms_bonds(self, atoms: list[dict], bonds: list[dict]) -> Molecule:
        bond_map = {
            "single": BondType.SINGLE, 1: BondType.SINGLE,
            "double": BondType.DOUBLE, 2: BondType.DOUBLE,
            "triple": BondType.TRIPLE, 3: BondType.TRIPLE,
            "aromatic": BondType.AROMATIC,
        }
        molecule = Molecule()
        for atom_data in atoms:
            molecule.add_atom(
                atom_data.get("atom_symbol", "C"),
                atom_data.get("x", 0.0) * 10.0,
                atom_data.get("y", 0.0) * 10.0,
                formal_charge=atom_data.get("charge", 0),
            )
        for bond_data in bonds:
            endpoints = bond_data.get("endpoint_atoms", [0, 1])
            if len(endpoints) < 2:
                continue
            first, second = endpoints[:2]
            if first < molecule.num_atoms and second < molecule.num_atoms:
                molecule.add_bond(
                    first,
                    second,
                    bond_map.get(bond_data.get("bond_type"), BondType.SINGLE),
                )
        return molecule


class MoleculeRecognizer:
    """Recognizer facade; OSRA is the default backend."""

    def __init__(
        self,
        device: Optional[str] = None,
        backend: str = "osra",
        osra_executable: Optional[Union[str, Path]] = None,
        timeout: int = 120,
    ) -> None:
        selected = backend.lower()
        if selected == "osra":
            self._backend = OSRARecognizer(osra_executable, timeout)
        elif selected == "molscribe":
            self._backend = MolScribeRecognizer(device)
        else:
            raise ValueError("backend must be 'osra' or 'molscribe'")

    @property
    def backend_name(self) -> str:
        return self._backend.backend_name

    def recognize(self, image: ImageInput) -> Molecule:
        return self._backend.recognize(image)

    def recognize_to_smiles(self, image: ImageInput) -> str:
        return self._backend.recognize_to_smiles(image)
