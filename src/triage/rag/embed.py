"""Wrapper around the local sentence-transformers embedding model.

The model (``all-MiniLM-L6-v2``, ~80 MB) is downloaded once from Hugging Face and
cached on disk, then runs locally on CPU or Apple GPU (MPS). No API, no cost. The
rest of the project calls ``embed_texts`` and never touches sentence-transformers
or PyTorch directly, so the model can be swapped here alone.
"""

from __future__ import annotations

import functools

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384


def _pick_device() -> str:
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


@functools.lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    from transformers.utils import logging as hf_logging

    hf_logging.set_verbosity_error()
    return SentenceTransformer(MODEL_NAME, device=_pick_device())


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into unit-normalised vectors of length ``EMBED_DIM``."""
    if not texts:
        return []
    vectors = _model().encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
