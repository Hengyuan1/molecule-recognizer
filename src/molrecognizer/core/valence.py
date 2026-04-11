"""Valence checking for common elements."""

from __future__ import annotations

from dataclasses import dataclass

from .molecule import Molecule

# Allowed valences for common elements.
# Each element maps to a tuple of acceptable total-valence values
# (accounting for formal charge adjustments via the formula below).
STANDARD_VALENCES: dict[str, tuple[int, ...]] = {
    "H":  (1,),
    "B":  (3,),
    "C":  (4,),
    "N":  (3, 5),
    "O":  (2,),
    "F":  (1,),
    "Si": (4,),
    "P":  (3, 5),
    "S":  (2, 4, 6),
    "Cl": (1,),
    "Br": (1,),
    "I":  (1, 3, 5, 7),
    "Se": (2, 4, 6),
}


@dataclass
class ValenceWarning:
    atom_index: int
    element: str
    expected_valences: tuple[int, ...]
    actual_valence: int
    formal_charge: int

    def __str__(self) -> str:
        expected = "/".join(str(v) for v in self.expected_valences)
        return (
            f"Atom {self.atom_index} ({self.element}): "
            f"valence {self.actual_valence}, expected {expected}"
            f" (charge {self.formal_charge:+d})" if self.formal_charge else
            f"Atom {self.atom_index} ({self.element}): "
            f"valence {self.actual_valence}, expected {expected}"
        )


def check_valence(mol: Molecule) -> list[ValenceWarning]:
    """Check all atoms against standard valence rules.

    Returns a list of warnings for atoms whose bond-count
    doesn't match any allowed valence for their element
    (after accounting for formal charge).
    """
    warnings: list[ValenceWarning] = []

    for idx in range(mol.num_atoms):
        info = mol.get_atom_info(idx)
        element = info.element
        if element not in STANDARD_VALENCES:
            continue  # skip metals / rare elements

        allowed = STANDARD_VALENCES[element]
        # Effective valence = bonds only (explicit Hs are not tracked in our model)
        actual = len(info.neighbors)

        # Adjust allowed valences for formal charge:
        # A positive charge reduces the expected valence by that amount,
        # a negative charge increases it.  E.g. N+ expects 4 bonds, O- expects 1.
        charge = info.formal_charge
        adjusted_allowed = tuple(v - charge for v in allowed)

        if actual not in adjusted_allowed:
            warnings.append(ValenceWarning(
                atom_index=idx,
                element=element,
                expected_valences=adjusted_allowed,
                actual_valence=actual,
                formal_charge=charge,
            ))

    return warnings
