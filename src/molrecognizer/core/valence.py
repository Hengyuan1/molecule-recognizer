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


# Formal-charge auto-inference for common octet-rule atoms.
# (valence_electrons, neutral_bond_count, neutral_lone_pair_electrons)
# Expanded-octet atoms (S, P, Se, Si) are omitted — their extra bonds
# are commonly neutral (e.g. sulfoxide), so we don't auto-infer.
_CHARGE_INFERENCE: dict[str, tuple[int, int, int]] = {
    "N":  (5, 3, 2),
    "O":  (6, 2, 4),
    "B":  (3, 3, 0),
    "F":  (7, 1, 6),
    "Cl": (7, 1, 6),
    "Br": (7, 1, 6),
    "I":  (7, 1, 6),
}


def infer_formal_charge(element: str, bond_order_sum: float,
                        existing_charge: int = 0) -> int:
    """Infer the formal charge for display / SMILES purposes.

    If the atom already carries a non-zero *existing_charge*, it is
    returned as-is.  Otherwise, for common octet-rule atoms whose bond
    order sum exceeds the neutral bond count the charge is derived from
    the standard formula::

        FC = valence_e − lone_pair_e − bond_order_sum

    where lone pairs decrease as extra bonds are formed.

    Returns 0 for elements not in the inference table or when the bond
    order sum does not exceed the neutral count.
    """
    if existing_charge != 0:
        return existing_charge
    import math
    bos_int = math.ceil(bond_order_sum)
    data = _CHARGE_INFERENCE.get(element)
    if data is None or bos_int <= data[1]:
        return 0
    val_e, neutral_bonds, neutral_lone_e = data
    delta = bos_int - neutral_bonds
    lone_e = max(0, neutral_lone_e - 2 * delta)
    return val_e - lone_e - bos_int


def compute_display_hs(element: str, bond_order_sum: float,
                       formal_charge: int) -> int:
    """How many implicit Hs to show on an atom label.

    Returns 0 for neutral carbon (skeletal style) and for elements not
    in :data:`STANDARD_VALENCES`.  Charged carbons DO get Hs displayed.
    """
    if element not in STANDARD_VALENCES:
        return 0
    # Neutral carbon hides Hs (skeletal style) unless it has no bonds
    # (isolated atom → show all Hs, e.g. CH₄)
    if element == "C" and formal_charge == 0 and bond_order_sum > 0:
        return 0
    # Effective valences: positive charge → more bonds, negative → fewer.
    adjusted = sorted(v + formal_charge for v in STANDARD_VALENCES[element])
    bos = int(round(bond_order_sum))
    for v in adjusted:
        if v >= bos:
            return max(0, v - bos)
    return 0  # hypervalent


def check_valence(mol: Molecule) -> list[ValenceWarning]:
    """Check all atoms against standard valence rules.

    Uses the total valence from RDKit (sum of bond orders + explicit Hs)
    and warns only when it **exceeds** the maximum allowed valence for the
    element.  Under-valence is normal — implicit hydrogens fill the gap.
    """
    warnings: list[ValenceWarning] = []

    for idx in range(mol.num_atoms):
        info = mol.get_atom_info(idx)
        element = info.element
        if element not in STANDARD_VALENCES:
            continue  # skip metals / rare elements

        allowed = STANDARD_VALENCES[element]
        # Bond-order sum = total valence minus any Hs (which are not drawn
        # on screen in skeletal structures).  This is what the user sees.
        actual = info.total_valence - info.implicit_hs - info.explicit_hs

        # Adjust allowed valences for formal charge:
        # A positive charge reduces the expected valence by that amount,
        # a negative charge increases it.  E.g. N+ expects 4 bonds, O- expects 1.
        charge = info.formal_charge
        adjusted_allowed = tuple(v - charge for v in allowed)

        # Only warn if the total valence exceeds the maximum the element
        # can accommodate.  Atoms below max valence simply have implicit Hs.
        if actual > max(adjusted_allowed):
            warnings.append(ValenceWarning(
                atom_index=idx,
                element=element,
                expected_valences=adjusted_allowed,
                actual_valence=actual,
                formal_charge=charge,
            ))

    return warnings
