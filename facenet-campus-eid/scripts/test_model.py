#!/usr/bin/env python
"""Smoke-test the FaceNet model and MTCNN imports."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch

from app.embedding_service import FaceEmbeddingService
from app.face_detector import MTCNNFaceDetector


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    detector = MTCNNFaceDetector()
    embedding_service = FaceEmbeddingService(device=detector.device)
    dummy_face = torch.zeros((3, 160, 160), dtype=torch.float32)
    embedding = embedding_service.generate_embedding(dummy_face)
    print(f"Device: {embedding_service.device}")
    print(f"Detector: {detector.__class__.__name__}")
    print(f"Embedding shape: {embedding.shape}")
    print(f"Embedding norm: {float(torch.linalg.vector_norm(torch.from_numpy(embedding))):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

