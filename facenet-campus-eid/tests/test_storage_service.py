from __future__ import annotations

import numpy as np
import pytest

from app.config import AppSettings
from app.storage_service import DuplicateUserError, StorageService


def test_saving_and_loading_embeddings(tmp_path) -> None:
    service = _storage(tmp_path)
    embedding = _embedding()
    metadata = {"name": "Mohamed Anas", "role": "student", "number_of_samples": 10}

    service.save_user_embedding("STU001", embedding, metadata)

    loaded_embedding = service.load_user_embedding("STU001")
    loaded_metadata = service.load_metadata("STU001")
    assert np.allclose(loaded_embedding, embedding)
    assert loaded_metadata["user_id"] == "STU001"
    assert loaded_metadata["name"] == "Mohamed Anas"


def test_duplicate_user_validation(tmp_path) -> None:
    service = _storage(tmp_path)
    service.save_user_embedding("STU001", _embedding(), {"name": "First"})

    with pytest.raises(DuplicateUserError):
        service.save_user_embedding("STU001", _embedding(), {"name": "Second"})


def test_overwrite_duplicate_user(tmp_path) -> None:
    service = _storage(tmp_path)
    service.save_user_embedding("STU001", _embedding(0), {"name": "First"})
    replacement = _embedding(1)

    service.save_user_embedding("STU001", replacement, {"name": "Second"}, overwrite=True)

    assert np.allclose(service.load_user_embedding("STU001"), replacement)
    assert service.load_metadata("STU001")["name"] == "Second"


def test_corrupted_file_handling_skips_bad_entry(tmp_path) -> None:
    service = _storage(tmp_path)
    service.save_user_embedding("STU001", _embedding(), {"name": "Valid"})
    bad_path = service.embedding_path("BAD001")
    bad_path.write_text("not an npz file", encoding="utf-8")

    loaded = service.load_all_embeddings()

    assert list(loaded) == ["STU001"]


def _storage(tmp_path) -> StorageService:
    settings = AppSettings(
        project_root=tmp_path,
        enrolled_faces_dir=tmp_path / "data" / "enrolled_faces",
        embeddings_dir=tmp_path / "data" / "embeddings",
        events_dir=tmp_path / "data" / "events",
        event_log_path=tmp_path / "data" / "events" / "access_events.jsonl",
    )
    return StorageService(settings)


def _embedding(index: int = 0) -> np.ndarray:
    embedding = np.zeros(512, dtype=np.float32)
    embedding[index] = 1.0
    return embedding

