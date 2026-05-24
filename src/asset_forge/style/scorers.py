"""Style scorers: pluggable backends that produce per-image embeddings.

Two implementations:

    HistogramScorer    Zero-dependency RGB histogram. Fast, no model
                       download. Good baseline. Used by default + in
                       CI tests.

    ClipScorer         OpenCLIP ViT-L/14. Loads on demand; gracefully
                       falls back to HistogramScorer if torch/openclip
                       not installed. Better fidelity when available.

Both produce normalized vectors; review_pack_style compares them via
cosine similarity to a reference (either the pack's hero image, or
the centroid of all piece embeddings).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image

from asset_forge.common.logging import get_logger

_log = get_logger("style.scorer")


class StyleScorer(ABC):
    """Abstract image -> embedding scorer."""

    name: str

    @abstractmethod
    def embed(self, image_path: Path) -> tuple[float, ...]:
        """Return a unit-norm embedding vector."""

    @staticmethod
    def cosine_similarity(a: tuple[float, ...], b: tuple[float, ...]) -> float:
        """0..1. 1 = identical direction."""
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
        sim = dot / (norm_a * norm_b)
        # Cosine can be in [-1, 1]; remap to [0, 1] for friendly threshold use
        return max(0.0, min((sim + 1.0) / 2.0, 1.0))


class HistogramScorer(StyleScorer):
    """RGB histogram embedding. 24 bins (8 per channel)."""

    name = "histogram"

    def __init__(self, bins_per_channel: int = 8, resize: int = 256) -> None:
        if bins_per_channel < 2 or bins_per_channel > 32:
            raise ValueError("bins_per_channel must be in [2, 32]")
        self._bins = bins_per_channel
        self._resize = resize

    def embed(self, image_path: Path) -> tuple[float, ...]:
        if not image_path.exists():
            return ()
        try:
            with Image.open(image_path) as raw:
                processed = raw.convert("RGB").resize((self._resize, self._resize))
                hist = processed.histogram()  # 768 ints: R[0..255], G[0..255], B[0..255]
        except (OSError, ValueError) as e:
            _log.warning("histogram.read_failed", path=str(image_path), error=str(e))
            return ()

        # Compress 256-bin per-channel histogram into <bins_per_channel> bins.
        bin_width = 256 // self._bins
        compressed: list[float] = []
        for channel in range(3):
            channel_hist = hist[channel * 256 : (channel + 1) * 256]
            for b in range(self._bins):
                bucket = channel_hist[b * bin_width : (b + 1) * bin_width]
                compressed.append(float(sum(bucket)))

        # Normalize to unit length
        total = math.sqrt(sum(x * x for x in compressed))
        if total == 0:
            return tuple(compressed)
        return tuple(x / total for x in compressed)


class ClipScorer(StyleScorer):
    """OpenCLIP ViT-L/14 embedding. Falls back to HistogramScorer if
    torch+open_clip aren't installed.

    Loads model once per process. ~4 GB VRAM at inference time.
    """

    name = "clip"

    def __init__(self, model_name: str = "ViT-L-14", pretrained: str = "openai") -> None:
        self._model_name = model_name
        self._pretrained = pretrained
        self._model = None
        self._preprocess = None
        self._fallback = HistogramScorer()

    def _ensure_loaded(self) -> bool:
        if self._model is not None:
            return True
        try:
            import open_clip
            import torch
        except ImportError:
            _log.warning("clip.unavailable", fallback="histogram")
            return False
        try:
            model, _, preprocess = open_clip.create_model_and_transforms(
                self._model_name, pretrained=self._pretrained
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(device).eval()
            self._model = model
            self._preprocess = preprocess
            self._device = device
            _log.info("clip.loaded", model=self._model_name, device=device)
            return True
        except Exception as e:
            _log.warning("clip.load_failed", error=str(e), fallback="histogram")
            return False

    def embed(self, image_path: Path) -> tuple[float, ...]:
        if not self._ensure_loaded():
            return self._fallback.embed(image_path)
        assert self._model is not None and self._preprocess is not None

        try:
            import torch

            with Image.open(image_path) as raw:
                img_rgb = raw.convert("RGB")
            tensor = self._preprocess(img_rgb).unsqueeze(0).to(self._device)
            with torch.no_grad():
                features = self._model.encode_image(tensor)
                features = features / features.norm(dim=-1, keepdim=True)
            return tuple(float(x) for x in features[0].cpu().numpy())
        except Exception as e:
            _log.warning(
                "clip.embed_failed", path=str(image_path), error=str(e), fallback="histogram"
            )
            return self._fallback.embed(image_path)
