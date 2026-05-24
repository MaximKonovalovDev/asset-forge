# retopo — auto-retopology

Wraps multiple backends behind one interface. AI-generated meshes
come out dense, triangulated, and unsuitable for animation/deformation.
This module fixes that.

## Contract

```python
from asset_forge.retopo import retopo_piece, TopologyTarget

result = await retopo_piece(
    input_glb=Path("out/raw/barrel.glb"),
    target=TopologyTarget(
        target_face_count=2000,
        quads_preferred=True,
        preserve_uvs=False,  # we re-unwrap after
        symmetric_axis="z",
    ),
)
# result.output_glb, result.face_count, result.is_quad_dominant
```

## Backends

| Backend | License | Quality | Speed | When to use |
|---|---|---|---|---|
| **Instant Meshes** | GPL but CLI-only | High (quad-dominant) | Fast | Default for organic shapes |
| **QuadriFlow** | BSD | High (true quads) | Slow | When clean topology is critical |
| **QuadRemesher** | Commercial ($109) | Best in class | Fast | When budget allows, complex shapes |
| **Blender Voxel Remesh** | GPL via Blender | OK (dense) | Very fast | Hard-surface props, low-poly target |
| **Blender Decimate** | GPL via Blender | OK (triangles) | Very fast | Quick LOD-style reduction |

Backend chosen per piece via heuristic:
- Organic + animation-bound → Instant Meshes
- Hard-surface props → Decimate
- Hero asset → QuadRemesher (if licensed)
- Pure procedural / collision → Voxel Remesh

## What we steal

- **Instant Meshes CLI** (GPL — used as subprocess, doesn't taint
  our proprietary code)
- **Blender's built-in voxel remesh + decimate** (via flax-blender-
  bridge)
- **MutaMesh patterns** (commercial Blender retopo plugin; reference
  for symmetry handling)

## License caution

Instant Meshes is GPL. We invoke it as a CLI subprocess and consume
its output (mesh data). Per FSF/GPL guidance: invoking GPL software
via shell / subprocess does NOT make our code derivative work. The
mesh OUTPUT is data, not code. Safe to ship asset-forge proprietary
+ instantmeshes.exe as a bundled binary with its GPL license file.

Verify before launch: legal review of CLI-subprocess GPL boundary.
