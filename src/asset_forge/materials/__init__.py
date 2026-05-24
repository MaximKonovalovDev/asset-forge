"""materials \u2014 PBR material library + palette-constrained assignment."""

from __future__ import annotations

from .api import (
    MaterialChoice,
    MaterialResult,
    assign_pack_materials,
    assign_piece_material,
)
from .library import MATERIAL_LIBRARY, MaterialEntry, find_materials_for_category

__all__ = [
    "MATERIAL_LIBRARY",
    "MaterialChoice",
    "MaterialEntry",
    "MaterialResult",
    "assign_pack_materials",
    "assign_piece_material",
    "find_materials_for_category",
]
