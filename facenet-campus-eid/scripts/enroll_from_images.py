#!/usr/bin/env python
"""Enroll one campus user from existing face images."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np

from app import config
from app.embedding_service import EmbeddingError, FaceEmbeddingService
from app.face_detector import MTCNNFaceDetector
from app.quality_service import FaceQualityService, QualityResult
from app.recognition_service import l2_normalize
from app.storage_service import DuplicateUserError, StorageService

LOGGER = logging.getLogger(__name__)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
ALWAYS_REJECT_REASONS = {"no_face", "multiple_faces", "low_detection_confidence"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enroll a campus user from existing image files.")
    parser.add_argument("--user-id", required=True, help="Unique campus user ID, for example TEA001")
    parser.add_argument("--name", required=True, help="Display name")
    parser.add_argument("--role", required=True, help="Campus role, for example teacher or student")
    parser.add_argument(
        "--images",
        required=True,
        nargs="+",
        help="Image file(s) or folder(s) containing enrollment pictures.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing enrollment for this user ID")
    parser.add_argument("--min-face-size", type=int, default=config.MIN_FACE_SIZE)
    parser.add_argument("--blur-threshold", type=float, default=config.BLUR_THRESHOLD)
    parser.add_argument(
        "--allow-low-quality",
        action="store_true",
        help="Accept images with size/blur/brightness/border warnings when one confident face is detected.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args()

    settings = config.AppSettings(min_face_size=args.min_face_size, blur_threshold=args.blur_threshold)
    config.ensure_data_directories(settings)
    storage = StorageService(settings)
    user_already_exists = storage.user_exists(args.user_id)
    if user_already_exists and not args.overwrite:
        raise SystemExit(f"user ID already exists: {args.user_id}. Use --overwrite to replace it.")

    image_paths = resolve_image_paths(args.images)
    if not image_paths:
        raise SystemExit("No enrollment images found.")

    detector = MTCNNFaceDetector(
        confidence_threshold=settings.detection_confidence_threshold,
        max_detection_width=settings.detection_max_width,
    )
    quality_service = FaceQualityService(
        min_face_size=settings.min_face_size,
        confidence_threshold=settings.detection_confidence_threshold,
        blur_threshold=settings.blur_threshold,
        min_brightness=settings.min_brightness,
        max_brightness=settings.max_brightness,
        border_margin_ratio=settings.face_border_margin_ratio,
    )
    embedding_service = FaceEmbeddingService(device=detector.device)

    embeddings: list[np.ndarray] = []
    accepted_frames: list[tuple[np.ndarray, Path]] = []

    LOGGER.info("Image enrollment started for %s using %d image(s)", args.user_id, len(image_paths))
    for image_path in image_paths:
        frame = cv2.imread(str(image_path))
        if frame is None:
            LOGGER.warning("Skipping unreadable image: %s", image_path)
            continue

        detections = detector.detect_bgr(frame)
        quality = quality_service.evaluate(frame, detections, require_single_face=True)
        if not should_accept_quality(quality, args.allow_low_quality):
            LOGGER.warning(
                "Skipping %s: %s sharpness=%.1f brightness=%.1f",
                image_path.name,
                quality.reason,
                quality.sharpness,
                quality.brightness,
            )
            continue

        detection = detections[0]
        if detection.aligned_face is None:
            LOGGER.warning("Skipping %s: face alignment failed", image_path.name)
            continue

        try:
            embedding = embedding_service.generate_embedding(detection.aligned_face)
        except EmbeddingError as exc:
            LOGGER.warning("Skipping %s: embedding failed: %s", image_path.name, exc)
            continue

        sample_number = len(embeddings) + 1
        embeddings.append(embedding)
        accepted_frames.append((frame, image_path))
        status = "accepted" if quality.valid else f"accepted_with_warning:{quality.reason}"
        LOGGER.info("%s %s as sample_%03d", status, image_path.name, sample_number)

    if not embeddings:
        raise SystemExit("No valid enrollment images were accepted.")

    if user_already_exists:
        storage.delete_user(args.user_id)
    user_faces_dir = storage.user_faces_dir(args.user_id)
    user_faces_dir.mkdir(parents=True, exist_ok=True)
    saved_image_names = save_accepted_frames(user_faces_dir, accepted_frames)

    average_embedding = l2_normalize(np.mean(np.vstack(embeddings), axis=0))
    metadata = {
        "user_id": args.user_id,
        "name": args.name,
        "role": args.role,
        "number_of_samples": len(embeddings),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": config.EMBEDDING_MODEL_NAME,
        "enrollment_source": "image_files",
        "stored_images": saved_image_names,
    }
    try:
        storage.save_user_embedding(
            args.user_id,
            average_embedding,
            metadata,
            sample_embeddings=np.vstack(embeddings),
            overwrite=True,
        )
    except DuplicateUserError as exc:
        LOGGER.error("%s", exc)
        return 1

    LOGGER.info("Enrollment success for %s (%s) from %d image(s)", args.user_id, args.name, len(embeddings))
    return 0


def should_accept_quality(quality: QualityResult, allow_low_quality: bool) -> bool:
    if quality.valid:
        return True
    if not allow_low_quality:
        return False
    return quality.reason not in ALWAYS_REJECT_REASONS


def resolve_image_paths(raw_paths: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw_path in raw_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            paths.append(path)
        elif path.is_dir():
            paths.extend(sorted(child for child in path.iterdir() if child.suffix.lower() in IMAGE_EXTENSIONS))
        else:
            LOGGER.warning("Ignoring unsupported image path: %s", raw_path)
    return sorted(dict.fromkeys(paths))


def normalized_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:
        return suffix
    return ".jpg"


def save_accepted_frames(user_faces_dir: Path, accepted_frames: list[tuple[np.ndarray, Path]]) -> list[str]:
    saved_image_names: list[str] = []
    for index, (frame, source_path) in enumerate(accepted_frames, start=1):
        stored_name = f"sample_{index:03d}{normalized_suffix(source_path)}"
        cv2.imwrite(str(user_faces_dir / stored_name), frame)
        saved_image_names.append(stored_name)
    return saved_image_names


if __name__ == "__main__":
    raise SystemExit(main())
