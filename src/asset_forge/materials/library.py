"""Curated PBR material library.

Each entry is a stylized procedural material recipe with:
  - base_color (hex)        the dominant palette color
  - roughness (0..1)
  - metallic (0..1)
  - category_tags (which piece categories this material naturally fits)
  - style_tags              ('warm', 'cold', 'natural', 'metallic', ...)

These are NOT external assets that need licensing \u2014 the recipes get
materialized into Blender shader graphs at material-assignment time
via flax-blender-bridge. Material Maker integration (importing .mat
files) is future work.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class MaterialEntry:
    id: str
    name: str
    base_color: str  # hex #RRGGBB
    roughness: float
    metallic: float
    category_tags: tuple[str, ...]
    style_tags: tuple[str, ...] = ()
    description: str = ""
    extra_params: dict[str, float] = field(default_factory=dict)


# Curated library. Spans typical low-poly fantasy / sci-fi / archviz needs.
# Keep this list intentionally small (~25 entries) so palette matching is fast.
MATERIAL_LIBRARY: tuple[MaterialEntry, ...] = (
    # --- Wood family ---
    MaterialEntry(
        id="wood_oak", name="Oak Wood", base_color="#604030", roughness=0.85, metallic=0.0,
        category_tags=("container", "furniture", "vessel", "weapon", "transport"),
        style_tags=("warm", "natural"),
    ),
    MaterialEntry(
        id="wood_dark", name="Dark Wood", base_color="#3a2418", roughness=0.78, metallic=0.0,
        category_tags=("container", "furniture", "vessel"),
        style_tags=("warm", "natural"),
    ),
    MaterialEntry(
        id="wood_light", name="Light Pine", base_color="#a0784c", roughness=0.88, metallic=0.0,
        category_tags=("container", "furniture", "transport"),
        style_tags=("warm", "natural"),
    ),
    # --- Metal family ---
    MaterialEntry(
        id="iron", name="Iron", base_color="#606060", roughness=0.55, metallic=0.9,
        category_tags=("weapon", "blacksmith", "lighting", "container"),
        style_tags=("cold", "metallic"),
    ),
    MaterialEntry(
        id="rusted_iron", name="Rusted Iron", base_color="#8a4a2c", roughness=0.85, metallic=0.4,
        category_tags=("weapon", "blacksmith", "container"),
        style_tags=("warm", "metallic", "aged"),
    ),
    MaterialEntry(
        id="brass", name="Brass", base_color="#c4a85a", roughness=0.35, metallic=0.85,
        category_tags=("lighting", "vessel"),
        style_tags=("warm", "metallic"),
    ),
    MaterialEntry(
        id="steel_polished", name="Polished Steel", base_color="#a0a0a4", roughness=0.18, metallic=0.95,
        category_tags=("weapon", "blacksmith"),
        style_tags=("cold", "metallic"),
    ),
    # --- Stone / earth ---
    MaterialEntry(
        id="stone_grey", name="Grey Stone", base_color="#7a7c80", roughness=0.92, metallic=0.0,
        category_tags=("nature", "blacksmith"),
        style_tags=("cold", "natural"),
    ),
    MaterialEntry(
        id="stone_mossy", name="Mossy Stone", base_color="#5a6a40", roughness=0.95, metallic=0.0,
        category_tags=("nature",),
        style_tags=("natural", "warm"),
    ),
    MaterialEntry(
        id="dirt", name="Dirt", base_color="#5a3e28", roughness=0.98, metallic=0.0,
        category_tags=("nature",),
        style_tags=("natural", "warm"),
    ),
    # --- Cloth / leather ---
    MaterialEntry(
        id="burlap", name="Burlap", base_color="#a08858", roughness=0.92, metallic=0.0,
        category_tags=("container",),
        style_tags=("warm", "natural", "fabric"),
    ),
    MaterialEntry(
        id="leather_brown", name="Brown Leather", base_color="#5a3a24", roughness=0.75, metallic=0.0,
        category_tags=("weapon", "misc"),
        style_tags=("warm", "natural"),
    ),
    # --- Ceramic / glass ---
    MaterialEntry(
        id="clay", name="Painted Clay", base_color="#c08070", roughness=0.68, metallic=0.0,
        category_tags=("vessel",),
        style_tags=("warm", "natural"),
    ),
    MaterialEntry(
        id="glass_green", name="Green Glass", base_color="#608060", roughness=0.10, metallic=0.0,
        category_tags=("vessel",),
        style_tags=("cool",),
        extra_params={"transmission": 0.9, "ior": 1.45},
    ),
    # --- Nature ---
    MaterialEntry(
        id="mushroom_red", name="Mushroom Cap Red", base_color="#a04040", roughness=0.55, metallic=0.0,
        category_tags=("nature",),
        style_tags=("warm",),
    ),
    MaterialEntry(
        id="mushroom_white", name="Mushroom Stem", base_color="#e6dccc", roughness=0.78, metallic=0.0,
        category_tags=("nature",),
        style_tags=("warm",),
    ),
    MaterialEntry(
        id="bark", name="Tree Bark", base_color="#4a3a26", roughness=0.95, metallic=0.0,
        category_tags=("nature",),
        style_tags=("warm", "natural"),
    ),
    # --- Sci-fi family (for future packs) ---
    MaterialEntry(
        id="scifi_panel", name="Sci-fi Panel", base_color="#404048", roughness=0.45, metallic=0.7,
        category_tags=("scifi", "container"),
        style_tags=("cold", "metallic"),
    ),
    MaterialEntry(
        id="scifi_emissive_blue", name="Sci-fi Emissive Blue", base_color="#80c0ff", roughness=0.30, metallic=0.5,
        category_tags=("scifi", "lighting"),
        style_tags=("cold",),
        extra_params={"emission_strength": 2.0},
    ),
    # --- Paper / parchment ---
    MaterialEntry(
        id="parchment", name="Parchment", base_color="#e0d4a8", roughness=0.85, metallic=0.0,
        category_tags=("misc",),
        style_tags=("warm", "natural"),
    ),
    MaterialEntry(
        id="book_leather", name="Book Leather", base_color="#5a2820", roughness=0.78, metallic=0.0,
        category_tags=("misc",),
        style_tags=("warm",),
    ),
    # --- Generic fallback ---
    MaterialEntry(
        id="generic_grey", name="Generic Grey", base_color="#808080", roughness=0.7, metallic=0.0,
        category_tags=("misc", "container", "furniture", "weapon", "vessel", "lighting", "transport", "blacksmith", "nature"),
        style_tags=(),
    ),
)


def find_materials_for_category(category: str) -> tuple[MaterialEntry, ...]:
    """Return all library entries whose category_tags include `category`."""
    category_lower = category.lower()
    return tuple(m for m in MATERIAL_LIBRARY if category_lower in m.category_tags)


def find_material_by_id(material_id: str) -> MaterialEntry | None:
    for m in MATERIAL_LIBRARY:
        if m.id == material_id:
            return m
    return None
