from __future__ import annotations

import numpy as np
import pytest

from app.embedding_service import FaceEmbeddingService


def test_l2_embedding_normalization() -> None:
    embedding = np.array([3.0, 4.0] + [0.0] * 510, dtype=np.float32)

    normalized = FaceEmbeddingService.normalize_embedding(embedding)

    assert normalized.shape == (512,)
    assert np.isclose(np.linalg.norm(normalized), 1.0)
    assert np.isclose(normalized[0], 0.6)
    assert np.isclose(normalized[1], 0.8)


def test_zero_embedding_normalization_rejected() -> None:
    with pytest.raises(ValueError):
        FaceEmbeddingService.normalize_embedding(np.zeros(512, dtype=np.float32))

