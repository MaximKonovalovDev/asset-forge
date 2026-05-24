# Kaggle backend for asset-forge

How asset-forge uses Kaggle Notebooks as a free batch-GPU backend.

## Why Kaggle

- **30 GPU hrs/week free per account** (P100 16 GB or T4×2 16 GB)
- **Stable quota** (unlike Colab's variable availability)
- Operator has 2 Google accounts → **60 GPU hrs/week free**
- Good for: heavier models that don't fit on local 6 GB (Hunyuan3D
  full, ControlNet style regen, AniGen experiments), batch retries
  when fal.ai $0.02/gen TRELLIS isn't good enough

## When to use Kaggle vs fal.ai

| Scenario | Backend |
|---|---|
| Production pack generation, per-piece | **fal.ai** (predictable, fast) |
| Batch retries with heavier model | **Kaggle** (free, slow) |
| Style consistency ControlNet pass | **Kaggle** (large model, batched) |
| AniGen character experiments | **Kaggle P100 16 GB** |
| One-off "what does this prompt look like?" | **fal.ai** ($0.02 cheaper than waiting) |

**fal.ai wins on convenience and speed. Kaggle wins on cost when
you have lots of pieces to process and time is OK.**

## Operator setup (one-time, per Kaggle account)

1. Go to https://www.kaggle.com/settings → API → "Create New Token"
2. Downloads `kaggle.json` with username + API key
3. In asset-forge `.env`:
   ```
   ASSET_FORGE_KAGGLE_USERNAME=<from kaggle.json>
   ASSET_FORGE_KAGGLE_API_TOKEN=<from kaggle.json>
   ```
4. For the SECOND Google account: same process, but you'll need to
   swap credentials when switching accounts. asset-forge supports
   this via `--kaggle-account=primary|secondary` flag (TBD).

## Notebook template

`asset_forge_batch.ipynb` is the notebook template that runs inside
Kaggle. It:

1. Reads a job spec from a Kaggle Dataset (which asset-forge
   uploads via `kaggle datasets create`)
2. Runs the requested model (Hunyuan3D full, AniGen, ControlNet,
   etc.) over the input pieces
3. Saves outputs to `/kaggle/working/`
4. asset-forge downloads outputs via `kaggle kernels output` after
   the run completes

The notebook is **uploaded via Kaggle API** as a new "version"
each batch — no manual web UI interaction needed once set up.

## How asset-forge drives Kaggle

```python
from asset_forge.mcp_client.backends.kaggle import KaggleBatchBackend

backend = KaggleBatchBackend(account="primary")

# Upload pieces + spec
batch_id = await backend.submit_batch(
    model="hunyuan3d-full",
    pieces=[piece1, piece2, ...],  # 10-20 pieces per batch
    timeout_minutes=120,
)

# Poll until done (Kaggle runs are typically 10-60 min)
result = await backend.wait_for_completion(batch_id)

# Download outputs
glb_paths = await backend.download_outputs(batch_id, dest=Path("out/raw/"))
```

## Quota management

The backend tracks per-account usage:

- Each successful run records its actual GPU duration
- Local SQLite tracks weekly usage per account
- Backend auto-switches to secondary account when primary hits 25/30 hrs
- Falls through to fal.ai when both accounts are at quota cap

## NOTE on Kaggle TOS

Kaggle's terms permit personal/research use; **commercial use is
explicitly allowed for the OUTPUTS you produce** but not for
running Kaggle's infrastructure as a paid service. We use Kaggle
to GENERATE assets we own; the assets are then sold via Fab/Unity/
Itch/Gumroad. This is within TOS.

We do NOT:
- Resell Kaggle compute as a service
- Run Kaggle notebooks for paying clients on their behalf
- Bypass Kaggle's quota system

If Kaggle changes their TOS or quota policy, the asset-forge
pipeline gracefully degrades: backend health check fails →
orchestrator routes to fal.ai → operator pays $0.02-$0.40/gen
instead. No pipeline outage.
