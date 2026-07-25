#!/usr/bin/env python
"""Enroll one campus user from webcam samples."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np

from app import config
from app.camera import Camera, draw_box, put_lines
from app.embedding_service import FaceEmbeddingService
from app.face_detector import MTCNNFaceDetector
from app.quality_service import FaceQualityService
from app.recognition_service import l2_normalize
from app.storage_service import DuplicateUserError, StorageService

LOGGER = logging.getLogger(__name__)

INSTRUCTIONS = [
    "Look straight",
    "Turn slightly left",
    "Turn slightly right",
    "Look slightly upward",
    "Look slightly downward",
    "Use a neutral expression",
    "Smile slightly",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enroll a campus user with webcam face samples.")
    parser.add_argument("--user-id", required=True, help="Unique campus user ID, for example STU001")
    parser.add_argument("--name", required=True, help="Display name")
    parser.add_argument("--role", required=True, help="Campus role, for example student or staff")
    parser.add_argument("--samples", type=int, default=config.ENROLLMENT_SAMPLES, help="Number of valid samples")
    parser.add_argument("--camera-index", type=int, default=config.CAMERA_INDEX)
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing enrollment for this user ID")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args()
    if args.samples < 1:
        raise SystemExit("--samples must be at least 1")

    settings = config.AppSettings(camera_index=args.camera_index, enrollment_samples=args.samples)
    config.ensure_data_directories(settings)
    storage = StorageService(settings)
    if storage.user_exists(args.user_id) and not args.overwrite:
        raise SystemExit(f"user ID already exists: {args.user_id}. Use --overwrite to replace it.")

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

    user_faces_dir = storage.user_faces_dir(args.user_id)
    user_faces_dir.mkdir(parents=True, exist_ok=True)
    embeddings: list[np.ndarray] = []
    captured_images = 0
    last_capture_at = 0.0
    window_name = "Campus E-ID Enrollment"

    camera: Camera | None = None
    try:
        camera = Camera(settings.camera_index)
        LOGGER.info("Enrollment started for %s on %s", args.user_id, detector.device)
        while captured_images < args.samples:
            ok, frame = camera.read()
            if not ok or frame is None:
                LOGGER.error("Frame read failure during enrollment")
                break

            raw_frame = frame.copy()
            detections = detector.detect_bgr(raw_frame)
            quality = quality_service.evaluate(raw_frame, detections, require_single_face=True)
            instruction = INSTRUCTIONS[captured_images % len(INSTRUCTIONS)]

            if detections:
                detection = detections[0]
                color = (0, 200, 0) if quality.valid else (0, 165, 255)
                label = f"{detection.probability:.2f}"
                draw_box(frame, detection.box, label, color)

            rejection = quality.reason or "ready"
            put_lines(
                frame,
                [
                    f"User: {args.user_id}  Samples: {captured_images}/{args.samples}",
                    f"Instruction: {instruction}",
                    f"Quality: {rejection}  sharpness={quality.sharpness:.1f} brightness={quality.brightness:.1f}",
                    "SPACE: capture  Q: quit",
                ],
            )
            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                LOGGER.info("Enrollment cancelled by user")
                return 1
            if key != 32:
                continue

            now = time.monotonic()
            if now - last_capture_at < settings.capture_delay_seconds:
                LOGGER.info("Capture skipped: wait %.1fs between samples", settings.capture_delay_seconds)
                continue
            if not quality.valid:
                LOGGER.info("Invalid enrollment sample: %s", quality.reason)
                continue
            detection = detections[0]
            if detection.aligned_face is None:
                LOGGER.info("Invalid enrollment sample: face alignment failed")
                continue

            embedding = embedding_service.generate_embedding(detection.aligned_face)
            image_path = user_faces_dir / f"sample_{captured_images + 1:03d}.jpg"
            cv2.imwrite(str(image_path), raw_frame)
            embeddings.append(embedding)
            captured_images += 1
            last_capture_at = now
            LOGGER.info("Captured valid sample %d/%d", captured_images, args.samples)

        if captured_images < args.samples:
            return 1

        average_embedding = l2_normalize(np.mean(np.vstack(embeddings), axis=0))
        metadata = {
            "user_id": args.user_id,
            "name": args.name,
            "role": args.role,
            "number_of_samples": captured_images,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "embedding_model": config.EMBEDDING_MODEL_NAME,
        }
        storage.save_user_embedding(args.user_id, average_embedding, metadata, overwrite=args.overwrite)
        LOGGER.info("Enrollment success for %s (%s)", args.user_id, args.name)
        return 0
    except DuplicateUserError as exc:
        LOGGER.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        LOGGER.info("Enrollment interrupted")
        return 1
    finally:
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
