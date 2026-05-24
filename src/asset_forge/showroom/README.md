# showroom — static-site generator for pack landing pages

Every pack gets its own landing page. Marketplaces (Fab/Unity/Itch)
have limited preview surface. We host our own showroom that:
- Shows every piece in 360° viewer
- Has video walkthrough auto-generated from Blender renders
- Links to all marketplace listings
- Captures email for the asset-forge newsletter
- Acts as the SEO + organic discovery channel we own

## Contract

```python
from asset_forge.showroom import build_site, SiteConfig

result = await build_site(
    pack_root=Path("out/001-fantasy-props/"),
    config=SiteConfig(
        output_dir=Path("showroom/dist/"),
        domain="assets.flax-game-studio.com",
        marketplace_links={
            "fab": "https://fab.com/...",
            "unity": "https://assetstore.unity.com/...",
            "itchio": "https://yourstudio.itch.io/...",
            "gumroad": "https://yourstudio.gumroad.com/l/...",
        },
    ),
)
# result.site_root, result.pages_generated, result.assets_total_mb
```

## What gets generated per pack

```
showroom/dist/001-fantasy-props/
├── index.html              # landing page with hero render + pricing
├── pieces/
│   ├── barrel.html         # per-piece page with 360 viewer
│   ├── crate.html
│   └── ...
├── demo-video.mp4          # auto-generated walkthrough
├── previews/               # all rendered previews
├── three-viewer/           # three.js GLB viewer assets
└── og-images/              # social preview images per piece
```

## The 360° viewer

Uses three.js + the master GLB per piece. Visitors can rotate,
zoom, see materials and topology. Critical for converting browsers
to buyers — marketplace screenshots can't compete.

## SEO

Per-piece pages auto-generate:
- `<title>`: "{Piece name} - {Pack name} - flax-game-studio"
- `<meta description>`: AI-generated description
- Structured data (schema.org/Product)
- og:image, og:video tags
- Sitemap.xml (root level)

This is the organic-discovery moat. Marketplace listings rank for
"buy fantasy pack." Showroom pages rank for "low-poly fantasy
barrel reference 3D model" and 100 other long-tail queries.

## Hosting

Default: Cloudflare Pages (free tier holds a year of growth)
- Auto-deploy on git push
- Custom domain via Cloudflare
- Free SSL
- Globally cached

Backup: Vercel free tier (same shape).

## What we steal

- **three.js GLB viewer** (MIT, the de-facto standard)
- **Astro / 11ty static-site patterns** (MIT, jinja-templated)
- **OpenAlternative's directory structure** (research'd earlier;
  proves the model works for sponsorship/SEO)
- **Synty's product page layout** (publicly visible, not their code)

## Newsletter capture

Embedded form posts to Buttondown / Beehiiv / ConvertKit (operator
picks). The newsletter is the asset-forge audience moat — owned
channel that marketplaces can't take from us.
