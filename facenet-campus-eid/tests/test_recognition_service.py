from __future__ import annotations

import numpy as np

from app.recognition_service import FaceRecognitionService, euclidean_distance, l2_normalize
from app.storage_service import StoredUser


def test_euclidean_distance_calculation() -> None:
    left = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    right = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    assert np.isclose(euclidean_distance(left, right), np.sqrt(2.0))


def test_best_match_selection() -> None:
    query = l2_normalize(_embedding_with_value(0, 1.0))
    enrolled = {
        "STU001": StoredUser("STU001", l2_normalize(_embedding_with_value(1, 1.0)), {"name": "Wrong"}),
        "STU002": StoredUser("STU002", query.copy(), {"name": "Correct", "role": "student"}),
    }

    result = FaceRecognitionService(threshold=0.5).recognize(query, enrolled)

    assert result.known is True
    assert result.user_id == "STU002"
    assert result.name == "Correct"
    assert np.isclose(result.distance, 0.0)


def test_unknown_person_threshold_behavior() -> None:
    query = l2_normalize(_embedding_with_value(0, 1.0))
    enrolled = {
        "STU001": StoredUser("STU001", l2_normalize(_embedding_with_value(1, 1.0)), {"name": "Far User"})
    }

    result = FaceRecognitionService(threshold=0.25).recognize(query, enrolled)

    assert result.known is False
    assert result.user_id is None
    assert result.name == "Unknown"
    assert result.distance is not None


def test_empty_database_returns_unknown() -> None:
    query = l2_normalize(_embedding_with_value(0, 1.0))

    result = FaceRecognitionService().recognize(query, {})

    assert result.known is False
    assert result.distance is None


def _embedding_with_value(index: int, value: float) -> np.ndarray:
    embedding = np.zeros(512, dtype=np.float32)
    embedding[index] = value
    return embedding

