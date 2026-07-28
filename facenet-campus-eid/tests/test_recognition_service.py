from __future__ import annotations

import numpy as np

from app.recognition_service import (
    FaceRecognitionService,
    euclidean_distance,
    l2_normalize,
    nearest_embedding_distance,
)
from app.storage_service import StoredUser


def test_euclidean_distance_calculation() -> None:
    left = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    right = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    assert np.isclose(euclidean_distance(left, right), np.sqrt(2.0))


def test_best_match_selection() -> None:
    query = l2_normalize(_embedding_with_value(0, 1.0))
    enrolled = {
        "STU001": _stored_user("STU001", l2_normalize(_embedding_with_value(1, 1.0)), {"name": "Wrong"}),
        "STU002": _stored_user("STU002", query.copy(), {"name": "Correct", "role": "student"}),
    }

    result = FaceRecognitionService(threshold=0.5).recognize(query, enrolled)

    assert result.known is True
    assert result.user_id == "STU002"
    assert result.name == "Correct"
    assert np.isclose(result.distance, 0.0)


def test_unknown_person_threshold_behavior() -> None:
    query = l2_normalize(_embedding_with_value(0, 1.0))
    enrolled = {
        "STU001": _stored_user("STU001", l2_normalize(_embedding_with_value(1, 1.0)), {"name": "Far User"})
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


def test_multi_sample_matching_uses_nearest_sample() -> None:
    query = l2_normalize(_embedding_with_value(0, 1.0))
    far_sample = l2_normalize(_embedding_with_value(1, 1.0))
    close_sample = query.copy()
    average = l2_normalize(far_sample + close_sample)
    enrolled = {
        "STU001": StoredUser(
            "STU001",
            average,
            np.vstack([far_sample, close_sample]),
            {"name": "Multi Sample User"},
        )
    }

    result = FaceRecognitionService(threshold=0.1).recognize(query, enrolled)

    assert result.known is True
    assert result.user_id == "STU001"
    assert np.isclose(result.distance, 0.0)


def test_nearest_embedding_distance_supports_single_vector() -> None:
    query = l2_normalize(_embedding_with_value(0, 1.0))

    distance = nearest_embedding_distance(query, query.copy())

    assert np.isclose(distance, 0.0)


def _stored_user(user_id: str, embedding: np.ndarray, metadata: dict) -> StoredUser:
    return StoredUser(user_id, embedding, embedding.reshape(1, -1), metadata)


def _embedding_with_value(index: int, value: float) -> np.ndarray:
    embedding = np.zeros(512, dtype=np.float32)
    embedding[index] = value
    return embedding
