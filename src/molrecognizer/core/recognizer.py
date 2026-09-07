"""Molecular structure recognition backends.

OSRA is the default backend and is invoked as a local command-line program.
MolScribe remains available as an explicit alternative.
"""

from __future__ import annotations

import io
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import warnings
from pathlib import Path
from threading import Event
from typing import Optional, Union

import numpy as np
from PIL import Image, ImageOps
from rdkit import Chem
from rdkit.Chem import AllChem

from .molecule import BondType, Molecule
from .layout import straighten_terminal_nitriles
from ..runtime import (application_directory, external_dll_search, is_frozen,
                       subprocess_options)

ImageInput = Union[str, Path, Image.Image, np.ndarray]

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# MolScribe models are expensive to load, so cache them by device.
_model_cache: dict[str, "MolScribeRecognizer"] = {}
_logger = logging.getLogger(__name__)


class RecognitionCancelled(Exception):
    """The caller cancelled a recognition job."""


def _unresolved_labels(mol: Chem.Mol) -> list[int]:
    """OCR aliases to retry, excluding intentional wildcard/R-group labels."""
    indices = []
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() != 0 or not atom.HasProp("molFileAlias"):
            continue
        label = atom.GetProp("molFileAlias").strip()
        if label and not re.fullmatch(r"R(?:\d+|['’]+|#)?|[XYZ*]|Ar|Het", label):
            indices.append(atom.GetIdx())
    return indices


def _merge_label_retry(original: Chem.Mol, retry: Chem.Mol) -> Chem.Mol:
    """Transfer unambiguous atom identities only; keep the original drawing.

    A retry with a different graph or stereo assignment is not evidence for a
    label correction. Check all mappings so symmetry cannot arbitrarily swap
    different atom labels. No unknown is ever assumed to mean carbon.
    """
    indices = _unresolved_labels(original)
    if (not indices or original.GetNumAtoms() != retry.GetNumAtoms()
            or original.GetNumBonds() != retry.GetNumBonds()):
        return original
    query = Chem.RWMol(original)
    for idx in indices:
        query.ReplaceAtom(idx, Chem.AtomFromSmarts("*"))
    matches = retry.GetSubstructMatches(query, useChirality=True, uniquify=False, maxMatches=65)
    if not matches or len(matches) >= 65:
        return original
    # Ordinary atoms in an RDKit substructure query don't constrain all
    # properties (notably formal charge). Known identities must also agree.
    known = [a for a in original.GetAtoms() if a.GetIdx() not in indices]
    def identity(atom):
        return atom.GetAtomicNum(), atom.GetFormalCharge(), atom.GetIsotope()
    matches = [match for match in matches
               if all(identity(atom) == identity(retry.GetAtomWithIdx(match[atom.GetIdx()]))
                      for atom in known)]
    if not matches:
        return original

    result = Chem.RWMol(original)
    for idx in indices:
        identities = set()
        for match in matches:
            atom = retry.GetAtomWithIdx(match[idx])
            identities.add((atom.GetAtomicNum(), atom.GetFormalCharge(), atom.GetIsotope(),
                            atom.GetNumExplicitHs(), atom.GetNoImplicit()))
        if len(identities) != 1:
            continue
        atomic_num, charge, isotope, hydrogens, no_implicit = identities.pop()
        if atomic_num == 0:
            continue
        atom = result.GetAtomWithIdx(idx)
        label = atom.GetProp("molFileAlias")
        atom.SetAtomicNum(atomic_num)
        atom.SetFormalCharge(charge)
        atom.SetIsotope(isotope)
        atom.SetNumExplicitHs(hydrogens)
        atom.SetNoImplicit(no_implicit)
        atom.ClearProp("molFileAlias")
        atom.SetProp("_OSRAOriginalAlias", label)
        _logger.info("OSRA label retry resolved atom %s: %s -> %s", idx, label, atom.GetSymbol())
    result.UpdatePropertyCache(strict=False)
    return result


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
        cancel_event: Optional[Event] = None,
    ) -> None:
        configured = executable or os.environ.get("OSRA_EXECUTABLE")
        resolved = shutil.which(str(configured)) if configured else None
        root = application_directory()
        # A portable release must use its tested OSRA, not an unrelated copy
        # on PATH. An explicit caller/environment override still wins.
        directories = [root / "tools" / "osra" / "bin",
                       root / ".tools" / "osra" / "bin"]
        if not is_frozen() and configured is None:
            resolved = shutil.which("osra")
            directories.reverse()
        if resolved is None and configured is None:
            names = ("osra.exe", "osra") if os.name == "nt" else ("osra", "osra.exe")
            for directory in directories:
                for name in names:
                    candidate = directory / name
                    if candidate.is_file():
                        resolved = str(candidate)
                        break
                if resolved is not None:
                    break
            if resolved is None:
                resolved = shutil.which("osra")
        if resolved is None:
            raise RuntimeError(
                "OSRA is the default recognizer, but its executable was not found. "
                "Install OSRA on PATH, set OSRA_EXECUTABLE, place it under "
                ".tools/osra/bin, or use MoleculeRecognizer(backend='molscribe')."
            )
        self.executable = resolved
        self.timeout = timeout
        self._cancel_event = cancel_event

    def _dictionary_options(self) -> list[str]:
        # Supply relocatable absolute paths: OSRA may have build-machine paths
        # compiled in. Never change the user's working directory to find data.
        binary = Path(self.executable).resolve()
        for directory in (binary.parent.parent / "share" / "osra",
                          binary.parent.parent / "share", binary.parent):
            names = (("-A", "chain.txt"), ("-l", "spelling.txt"),
                     ("-a", "superatom.txt"))
            if all((directory / name).is_file() for _, name in names):
                return [value for flag, name in names
                        for value in (flag, str(directory / name))]
        return []

    def _check_cancelled(self):
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise RecognitionCancelled("Recognition cancelled")

    def _run_osra(self, command, *, timeout, text=False):
        if self._cancel_event is None:
            # Do not hold the DLL-search lock while waiting for OSRA.
            if not is_frozen():
                return subprocess.run(command, capture_output=True, timeout=timeout,
                                      text=text, check=False, **subprocess_options())
        self._check_cancelled()
        # communicate() drains both pipes while waiting. Short time slices let
        # GUI shutdown cancel this process, without waiting on the GUI thread.
        with external_dll_search():
            process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=text,
                                       **subprocess_options())
        deadline = time.monotonic() + timeout
        try:
            while True:
                self._check_cancelled()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                try:
                    stdout, stderr = process.communicate(timeout=min(0.1, remaining))
                    self._check_cancelled()
                    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
                except subprocess.TimeoutExpired:
                    continue
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()  # Reap only this job's process, in the worker.

    def recognize(self, image: ImageInput) -> Molecule:
        if isinstance(image, np.ndarray):
            return self._recognize_pil_structure(Image.fromarray(image))
        if isinstance(image, Image.Image):
            return self._recognize_pil_structure(image)
        return self._recognize_structure_file(Path(image))

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

    def _recognize_pil_structure(self, image: Image.Image) -> Molecule:
        """Recognize a PIL image while preserving OSRA's drawing geometry."""
        temp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
                temp_path = Path(temp.name)
            image.save(temp_path, format="PNG")
            return self._recognize_structure_file(temp_path)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _recognize_structure_file(self, path: Path) -> Molecule:
        """Use SDF so coordinates and explicit bond placement survive."""
        rdmol = self._read_sdf(path)
        if rdmol is not None:
            rdmol = self._retry_small_image_labels(path, rdmol)
            self._check_cancelled()
            return Molecule.from_rdkit(straighten_terminal_nitriles(rdmol))

        # A few OSRA builds have incomplete SDF support. Retain recognition
        # through canonical SMILES, accepting that only this fallback redraws.
        return _smiles_to_molecule(self._recognize_file(path), self.backend_name)

    def _retry_small_image_labels(self, path: Path, mol: Chem.Mol) -> Chem.Mol:
        """One bounded 2x OCR retry for unresolved labels in small raster crops."""
        self._check_cancelled()
        if not _unresolved_labels(mol):
            return mol
        temp_path: Optional[Path] = None
        try:
            with Image.open(path) as source:
                if max(source.size) > 1200 or getattr(source, "n_frames", 1) != 1:
                    return mol
                rgba = source.convert("RGBA")
                image = Image.new("RGB", source.size, "white")
                image.paste(rgba, mask=rgba.getchannel("A"))
                image = image.resize((image.width * 2, image.height * 2), Image.Resampling.LANCZOS)
                image = ImageOps.expand(image, border=20, fill="white")
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
                temp_path = Path(temp.name)
            image.save(temp_path, format="PNG")
            retry = self._read_sdf(temp_path, timeout=min(self.timeout, 15))
            if retry is not None:
                return _merge_label_retry(mol, retry)
        except RecognitionCancelled:
            raise
        except Exception:
            # Optional recovery must not discard an otherwise usable result.
            _logger.debug("OSRA label retry failed; retaining the original result", exc_info=True)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
        return mol

    def _read_sdf(self, path: Path, timeout: Optional[int] = None,
                  *, options: tuple[str, ...] = ()) -> Optional[Chem.Mol]:
        if not path.is_file():
            raise FileNotFoundError(f"Image file not found: {path}")
        timeout = self.timeout if timeout is None else timeout
        command = [
            self.executable,
            "-f",
            "sdf",
            "--timeout",
            str(timeout),
            *self._dictionary_options(),
            *options,
            "--",
            str(path),
        ]
        try:
            result = self._run_osra(command, timeout=timeout + 10)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"OSRA recognition timed out after {timeout} seconds"
            ) from exc

        raw_output = result.stdout
        if isinstance(raw_output, str):
            raw_output = raw_output.encode("utf-8")
        if raw_output.strip():
            supplier = Chem.ForwardSDMolSupplier(
                io.BytesIO(raw_output),
                sanitize=False,
                removeHs=False,
                strictParsing=False,
            )
            for rdmol in supplier:
                if (rdmol is not None and rdmol.GetNumAtoms() > 0
                        and rdmol.GetNumConformers() > 0):
                    try:
                        rdmol.UpdatePropertyCache(strict=False)
                    except Exception:
                        pass
                    # The SDF reader converts wedge/dash codes into atom
                    # chirality and clears the visible bond directions. Restore
                    # the original markings (including their narrow endpoints),
                    # not WedgeMolBonds' choice of a new bond for each center.
                    Chem.ReapplyMolBlockWedging(rdmol)
                    return rdmol
        return None

    def _recognize_file(self, path: Path) -> str:
        if not path.is_file():
            raise FileNotFoundError(f"Image file not found: {path}")
        command = [
            self.executable,
            "-f",
            "can",
            "--timeout",
            str(self.timeout),
            *self._dictionary_options(),
            "--",
            str(path),
        ]
        try:
            result = self._run_osra(command, text=True, timeout=self.timeout + 10)
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
        cancel_event: Optional[Event] = None,
    ) -> None:
        selected = backend.lower()
        if selected == "osra":
            self._backend = OSRARecognizer(osra_executable, timeout, cancel_event)
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
