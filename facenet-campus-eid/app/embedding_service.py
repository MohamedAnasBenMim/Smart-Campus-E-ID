"""FaceNet embedding generation."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from app.config import EMBEDDING_DIMENSION, EMBEDDING_MODEL_NAME
from app.recognition_service import l2_normalize

LOGGER = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    """Raised when a face embedding cannot be generated."""


class FaceEmbeddingService:
    """Generate normalized FaceNet embeddings from aligned face tensors."""

    def __init__(self, model: Any | None = None, device: str | None = None) -> None:
        self.device = device or self.select_device()
        self.model = model if model is not None else self._load_model()
        if hasattr(self.model, "to"):
            self.model = self.model.to(self.device)
        if hasattr(self.model, "eval"):
            self.model.eval()
        LOGGER.info("Embedding model ready on %s", self.device)

    @staticmethod
    def select_device() -> str:
        """Return cuda when available, otherwise cpu."""

        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    @staticmethod
    def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
        """L2-normalize an embedding."""

        return l2_normalize(embedding)

    def generate_embedding(self, aligned_face: Any) -> np.ndarray:
        """Generate a 512-dimensional normalized NumPy embedding."""

        try:
            import torch

            if not torch.is_tensor(aligned_face):
                aligned_face = torch.as_tensor(aligned_face)
            tensor = aligned_face.float()
            if tensor.ndim == 3:
                tensor = tensor.unsqueeze(0)
            if tensor.ndim != 4:
                raise EmbeddingError(f"aligned face tensor must be 3D or 4D, got {tensor.ndim}D")
            tensor = tensor.to(self.device)

            with torch.no_grad():
                output = self.model(tensor)

            embedding = output.detach().cpu().numpy()
            if embedding.ndim == 2 and embedding.shape[0] == 1:
                embedding = embedding[0]
            embedding = np.asarray(embedding, dtype=np.float32)
            if embedding.shape != (EMBEDDING_DIMENSION,):
                raise EmbeddingError(
                    f"expected {EMBEDDING_DIMENSION}-dimensional embedding from {EMBEDDING_MODEL_NAME}, "
                    f"got {embedding.shape}"
                )
            return self.normalize_embedding(embedding)
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(f"FaceNet inference failed: {exc}") from exc

    def _load_model(self) -> Any:
        try:
            from facenet_pytorch import InceptionResnetV1

            return InceptionResnetV1(pretrained="vggface2").eval()
        except Exception as exc:
            raise EmbeddingError(
                "Could not load InceptionResnetV1(pretrained='vggface2'). "
                "Install requirements and ensure model weights can be downloaded."
            ) from exc

