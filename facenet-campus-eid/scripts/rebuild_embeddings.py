#!/usr/bin/env python
"""Rebuild average embeddings from saved enrollment images."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np

from app import config
from app.embedding_service import FaceEmbeddingService
from app.face_detector import MTCNNFaceDetector
from app.quality_service import FaceQualityService
from app.recognition_service import l2_normalize
from app.storage_service import StorageService

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild NPZ embeddings from enrolled face images.")
    parser.add_argument("--user-id", help="Rebuild one user only")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args()
    settings = config.AppSettings()
    config.ensure_data_directories(settings)
    storage = StorageService(settings)
    detector = MTCNNFaceDetector()
    quality_service = FaceQualityService()
    embedding_service = FaceEmbeddingService(device=detector.device)

    user_dirs = [storage.user_faces_dir(args.user_id)] if args.user_id else sorted(settings.enrolled_faces_dir.iterdir())
    rebuilt = 0
    for user_dir in user_dirs:
        if not user_dir.is_dir():
            continue
        user_id = user_dir.name
        embeddings: list[np.ndarray] = []
        for image_path in sorted(user_dir.glob("*.jpg")) + sorted(user_dir.glob("*.png")):
            frame = cv2.imread(str(image_path))
            if frame is None:
                LOGGER.warning("Skipping unreadable image: %s", image_path)
                continue
            detections = detector.detect_bgr(frame)
            quality = quality_service.evaluate(frame, detections, require_single_face=True)
            if not quality.valid or detections[0].aligned_face is None:
                LOGGER.warning("Skipping %s: %s", image_path.name, quality.reason)
                continue
            embeddings.append(embedding_service.generate_embedding(detections[0].aligned_face))

        if not embeddings:
            LOGGER.warning("No valid images for %s", user_id)
            continue
        metadata = storage.load_metadata(user_id)
        metadata["number_of_samples"] = len(embeddings)
        metadata["embedding_model"] = config.EMBEDDING_MODEL_NAME
        average_embedding = l2_normalize(np.mean(np.vstack(embeddings), axis=0))
        storage.save_user_embedding(user_id, average_embedding, metadata, overwrite=True)
        rebuilt += 1
        LOGGER.info("Rebuilt embedding for %s from %d images", user_id, len(embeddings))

    LOGGER.info("Rebuilt %d user embeddings", rebuilt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

