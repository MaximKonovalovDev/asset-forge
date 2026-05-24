"""Marketplace text/markdown templates.

Generated text fields per pack: README.md, license.txt, AI disclosure.
Each marketplace gets its own variant; templates stay close to the
source so they're easy to audit.
"""

from __future__ import annotations

from asset_forge.common.types import Brief


def pack_readme(brief: Brief) -> str:
    """Pack README. Reused across Fab/Unity/Itch/Gumroad with minor edits."""
    pieces_by_category: dict[str, list[str]] = {}
    for p in brief.pieces:
        pieces_by_category.setdefault(p.category, []).append(p.id)

    lines: list[str] = [
        f"# {brief.title}",
        "",
        brief.description.strip(),
        "",
        "## What's included",
        "",
        f"- **{len(brief.pieces)} pieces** across {len(pieces_by_category)} categories",
        f"- **Hero pieces:** {len(brief.hero_piece_ids)}",
        f"- **Polygon range:** {brief.style.polygon_count_band[0]}-{brief.style.polygon_count_band[1]} faces per piece",
        f"- **Texel density:** {brief.style.texel_density_px_per_unit} px/unit",
        "- **Demo scenes** for each target engine",
        "- Engine targets: " + ", ".join(brief.exports),
        "",
        "## Pieces by category",
        "",
    ]
    for category in sorted(pieces_by_category):
        lines.append(f"### {category}")
        lines.append("")
        for pid in pieces_by_category[category]:
            piece = brief.piece_by_id(pid)
            if piece is not None:
                lines.append(f"- `{pid}` \u2014 {piece.prompt}")
        lines.append("")

    lines.extend(
        [
            "## Style",
            "",
            f"- {brief.style.reference_description}",
            f"- Shading: {brief.style.shading}",
            f"- Material complexity: {brief.style.material_complexity}",
            "",
            "## Modular assembly",
            "",
            f"- Grid preset: `{brief.grid.preset}`",
            f"- Grid unit: {brief.grid.grid_unit_meters} m",
            f"- Pivot: {brief.grid.snap_pivot_to}",
            "",
            "## License",
            "",
            "See `license.txt`. Single-seat per purchase; multi-seat available on request.",
            "",
            "## AI disclosure",
            "",
            "See `ai_disclosure.txt`. All pieces reviewed by a human before release.",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def license_text(brief: Brief) -> str:
    """Standard per-pack EULA template. Operator can swap before shipping."""
    return (
        f"License for {brief.title}\n"
        "=" * 50 + "\n\n"
        "Copyright (c) 2026 flax-game-studio. All rights reserved.\n\n"
        "GRANT OF LICENSE\n"
        "----------------\n"
        "The purchaser is granted a non-exclusive, non-transferable\n"
        "license to use the included assets in their own commercial or\n"
        "non-commercial game projects, distributed to end users as part\n"
        "of a compiled game.\n\n"
        "PERMITTED USES\n"
        "--------------\n"
        " - Use in shipped games on any platform\n"
        " - Modification of the assets to suit your project\n"
        " - Use in unlimited end-user games per single-seat license\n\n"
        "PROHIBITED USES\n"
        "---------------\n"
        " - Resale or redistribution of the asset files themselves\n"
        " - Use in NFT collections or as standalone digital art for sale\n"
        " - Sharing across multiple developer seats (multi-seat sold separately)\n"
        " - Training of any machine learning model on these assets\n\n"
        "WARRANTY\n"
        "--------\n"
        "These assets are provided AS-IS. flax-game-studio does not\n"
        "warrant their fitness for any particular purpose.\n\n"
        "For licensing inquiries beyond this scope, contact via GitHub:\n"
        "https://github.com/flax-game-studio\n"
    )


def ai_disclosure_text(brief: Brief) -> str:
    """AI disclosure required by Fab + Unity marketplace policy."""
    models = ", ".join(brief.ai_disclosure.models_used)
    verified = (
        "Yes \u2014 commercial-use rights verified for each model."
        if brief.ai_disclosure.commercial_use_verified
        else "Pending operator verification."
    )
    return (
        f"AI Disclosure for {brief.title}\n"
        "=" * 50 + "\n\n"
        "This pack contains assets that were generated and refined using\n"
        "AI-assisted workflows. We disclose this in compliance with the\n"
        "Fab, Unity Asset Store, and Itch.io marketplace policies on\n"
        "AI-generated content.\n\n"
        "WHAT WAS AI-ASSISTED\n"
        "--------------------\n"
        " - Initial 3D mesh generation from text prompts\n"
        " - Automated retopology (mesh cleanup) via free, BSD/GPL CLI tools\n"
        " - UV unwrapping automated through Blender Smart UV Project\n"
        " - PBR material assignment from a curated procedural library\n\n"
        "WHAT WAS HUMAN-CURATED\n"
        "----------------------\n"
        " - Style direction (palette, shading, reference image)\n"
        " - Per-piece prompt engineering and review\n"
        " - Material tuning and final visual approval\n"
        " - Demo scene composition and pack curation\n"
        " - Topology validation and pivot/scale normalization review\n\n"
        f"MODELS USED: {models}\n\n"
        f"COMMERCIAL-USE RIGHTS: {verified}\n\n"
        f"REVIEW STATEMENT: {brief.ai_disclosure.human_review}\n"
    )
