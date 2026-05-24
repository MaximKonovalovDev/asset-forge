# common — shared types, settings, telemetry

The base layer everything else imports from. Keep this thin.

## Modules

- `types.py` — Pack, Piece, Brief, StyleSpec, Receipt dataclasses
- `settings.py` — pydantic-settings, reads .env
- `logging.py` — structlog setup
- `paths.py` — output path conventions (`out/<pack-id>/...`)
- `errors.py` — typed exception hierarchy (RetopoFailed, StyleOutlier, etc.)

## Conventions

```
out/<pack-id>/
├── .state.json                  resumable orchestrator state
├── raw/                         text-to-3D outputs (.glb)
├── retopo/                      after retopology
├── uv/                          after UV unwrap
├── materials/                   after material assignment
├── final/                       after style + snap_grid normalization
├── lods/                        with LOD chains
├── exports/
│   ├── unity/*.unitypackage
│   ├── unreal/*.zip
│   ├── godot/*.zip
│   └── master/*.glb
├── previews/                    Blender renders per piece
├── manifests/
│   ├── fab/                     submission bundle
│   ├── unity/                   submission bundle
│   ├── itchio/                  submission bundle
│   └── gumroad/                 submission bundle
└── receipts.ndjson              audit trail (every flax-mcp call)
```
