"""Local file storage for enrollment metadata and embeddings."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.config import AppSettings, EMBEDDING_DIMENSION, ensure_data_directories

LOGGER = logging.getLogger(__name__)


class StorageError(RuntimeError):
    """Raised when local enrollment storage cannot be read or written."""


class DuplicateUserError(StorageError):
    """Raised when an enrollment would overwrite an existing user."""


@dataclass(frozen=True)
class StoredUser:
    """Loaded embedding and metadata for one enrolled user."""

    user_id: str
    embedding: np.ndarray
    sample_embeddings: np.ndarray
    metadata: dict[str, Any]


class StorageService:
    """Store embeddings as NPZ files and user metadata as JSON."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.settings = settings or AppSettings()
        ensure_data_directories(self.settings)

    def user_exists(self, user_id: str) -> bool:
        """Return True if any local artifact exists for the user."""

        self._validate_user_id(user_id)
        return (
            self.embedding_path(user_id).exists()
            or self.metadata_path(user_id).exists()
            or self.user_faces_dir(user_id).exists()
        )

    def save_user_embedding(
        self,
        user_id: str,
        embedding: np.ndarray,
        metadata: dict[str, Any],
        *,
        sample_embeddings: np.ndarray | None = None,
        overwrite: bool = False,
    ) -> None:
        """Save one user's average embedding, sample embeddings, and metadata."""

        self._validate_user_id(user_id)
        if self.user_exists(user_id) and not overwrite:
            raise DuplicateUserError(f"user_id already exists: {user_id}")

        embedding = self._validate_embedding(embedding)
        samples = self._validate_sample_embeddings(sample_embeddings, fallback=embedding)
        self.embedding_path(user_id).parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(self.embedding_path(user_id), embedding=embedding, sample_embeddings=samples)
        self.save_metadata(user_id, metadata)

    def load_user_embedding(self, user_id: str) -> np.ndarray:
        """Load one embedding, validating its shape and contents."""

        self._validate_user_id(user_id)
        path = self.embedding_path(user_id)
        if not path.exists():
            raise StorageError(f"embedding file does not exist: {path}")

        try:
            with np.load(path) as data:
                if "embedding" not in data:
                    raise StorageError(f"missing 'embedding' array in {path}")
                return self._validate_embedding(data["embedding"])
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(f"could not load embedding from {path}: {exc}") from exc

    def load_user_sample_embeddings(self, user_id: str) -> np.ndarray:
        """Load all stored sample embeddings for one user.

        Older enrollment files may contain only the averaged embedding. In that
        case, return a one-row matrix so recognition stays backward compatible.
        """

        self._validate_user_id(user_id)
        path = self.embedding_path(user_id)
        if not path.exists():
            raise StorageError(f"embedding file does not exist: {path}")

        try:
            with np.load(path) as data:
                if "sample_embeddings" in data:
                    return self._validate_sample_embeddings(data["sample_embeddings"])
                if "embedding" not in data:
                    raise StorageError(f"missing embedding arrays in {path}")
                embedding = self._validate_embedding(data["embedding"])
                return embedding.reshape(1, -1)
        except StorageError:
            raise
        except Exception as exc:
            raise StorageError(f"could not load sample embeddings from {path}: {exc}") from exc

    def load_all_embeddings(self) -> dict[str, StoredUser]:
        """Load all valid embeddings, skipping corrupted entries with a warning."""

        users: dict[str, StoredUser] = {}
        for path in sorted(self.settings.embeddings_dir.glob("*.npz")):
            user_id = path.stem
            try:
                embedding = self.load_user_embedding(user_id)
                sample_embeddings = self.load_user_sample_embeddings(user_id)
                metadata = self.load_metadata(user_id)
                users[user_id] = StoredUser(
                    user_id=user_id,
                    embedding=embedding,
                    sample_embeddings=sample_embeddings,
                    metadata=metadata,
                )
            except StorageError as exc:
                LOGGER.warning("Skipping corrupted enrollment for %s: %s", user_id, exc)
        return users

    def delete_user(self, user_id: str) -> None:
        """Delete a user's embedding, metadata, and enrolled images if present."""

        self._validate_user_id(user_id)
        for path in (self.embedding_path(user_id), self.metadata_path(user_id)):
            if path.exists():
                path.unlink()
        faces_dir = self.user_faces_dir(user_id)
        if faces_dir.exists():
            shutil.rmtree(faces_dir)

    def save_metadata(self, user_id: str, metadata: dict[str, Any]) -> None:
        """Write JSON metadata for one enrolled user."""

        self._validate_user_id(user_id)
        payload = dict(metadata)
        payload["user_id"] = user_id
        path = self.metadata_path(user_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def load_metadata(self, user_id: str) -> dict[str, Any]:
        """Load user metadata, returning minimal metadata if the JSON is missing."""

        self._validate_user_id(user_id)
        path = self.metadata_path(user_id)
        if not path.exists():
            return {"user_id": user_id, "name": user_id, "role": None}

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise StorageError(f"could not load metadata from {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise StorageError(f"metadata is not a JSON object: {path}")
        return data

    def embedding_path(self, user_id: str) -> Path:
        """Return the local NPZ path for a user embedding."""

        self._validate_user_id(user_id)
        return self.settings.embeddings_dir / f"{user_id}.npz"

    def metadata_path(self, user_id: str) -> Path:
        """Return the local JSON metadata path for a user."""

        self._validate_user_id(user_id)
        return self.settings.embeddings_dir / f"{user_id}.json"

    def user_faces_dir(self, user_id: str) -> Path:
        """Return the enrollment-image directory for a user."""

        self._validate_user_id(user_id)
        return self.settings.enrolled_faces_dir / user_id

    @staticmethod
    def _validate_user_id(user_id: str) -> None:
        if not user_id or user_id.strip() != user_id:
            raise StorageError("user_id must be non-empty and must not contain surrounding spaces")
        if any(separator in user_id for separator in ("/", "\\")) or user_id in {".", ".."}:
            raise StorageError("user_id must not contain path separators")

    @staticmethod
    def _validate_embedding(embedding: np.ndarray) -> np.ndarray:
        array = np.asarray(embedding, dtype=np.float32)
        if array.shape != (EMBEDDING_DIMENSION,):
            raise StorageError(f"embedding must have shape ({EMBEDDING_DIMENSION},), got {array.shape}")
        if not np.isfinite(array).all():
            raise StorageError("embedding contains NaN or infinite values")
        return array

    @staticmethod
    def _validate_sample_embeddings(
        sample_embeddings: np.ndarray | None,
        *,
        fallback: np.ndarray | None = None,
    ) -> np.ndarray:
        if sample_embeddings is None:
            if fallback is None:
                raise StorageError("sample embeddings are missing")
            return StorageService._validate_embedding(fallback).reshape(1, -1)

        array = np.asarray(sample_embeddings, dtype=np.float32)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        if array.ndim != 2 or array.shape[1] != EMBEDDING_DIMENSION:
            raise StorageError(
                f"sample embeddings must have shape (n, {EMBEDDING_DIMENSION}), got {array.shape}"
            )
        if array.shape[0] < 1:
            raise StorageError("sample embeddings must contain at least one row")
        if not np.isfinite(array).all():
            raise StorageError("sample embeddings contain NaN or infinite values")
        return array
