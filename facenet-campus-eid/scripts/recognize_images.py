#!/usr/bin/env python
"""Recognize enrolled campus users in still images."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2

from app import config
from app.camera import put_lines
from app.embedding_service import FaceEmbeddingService
from app.event_logger import EventLogger
from app.face_detector import MTCNNFaceDetector
from app.liveness_service import LivenessService
from app.quality_service import FaceQualityService
from app.recognition_service import FaceRecognitionService, TemporalStabilizer
from app.storage_service import StorageService
from recognize_video import detect_faces, draw_detection_observations, resolve_output_path
from recognize_webcam import draw_observations, process_frame

LOGGER = logging.getLogger(__name__)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run face recognition on image files.")
    parser.add_argument(
        "--source",
        default="test_images",
        help="Image file or directory of images. Defaults to the project's test_images/ folder.",
    )
    parser.add_argument("--output", help="Optional annotated output image file or output directory.")
    parser.add_argument("--threshold", type=float, default=config.RECOGNITION_DISTANCE_THRESHOLD)
    parser.add_argument("--min-face-size", type=int, default=config.MIN_FACE_SIZE)
    parser.add_argument("--detect-only", action="store_true", help="Only draw detected faces; skip embeddings.")
    parser.add_argument("--display", action="store_true", help="Open each annotated image in an OpenCV window.")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args()
    settings = config.AppSettings(
        recognition_distance_threshold=args.threshold,
        min_face_size=args.min_face_size,
        tracking_confirmation_count=1,
    )
    config.ensure_data_directories(settings)

    image_paths = resolve_image_sources(PROJECT_ROOT / args.source)
    if not image_paths:
        raise SystemExit(f"No images found at {args.source}")

    output_base = Path(args.output) if args.output else None
    services = build_services(settings, detect_only=args.detect_only)

    exit_code = 0
    for image_path in image_paths:
        output_path = resolve_image_output_path(output_base, image_path, multiple=len(image_paths) > 1)
        ok = process_image(
            image_path,
            output_path,
            settings,
            services,
            detect_only=args.detect_only,
            display=args.display,
        )
        exit_code = 0 if ok and exit_code == 0 else 1
    cv2.destroyAllWindows()
    return exit_code


def build_services(settings: config.AppSettings, *, detect_only: bool) -> dict:
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
    services = {
        "detector": detector,
        "quality_service": quality_service,
    }
    if detect_only:
        LOGGER.info("Image detection-only mode ready on %s", detector.device)
        return services

    storage = StorageService(settings)
    enrolled_users = storage.load_all_embeddings()
    LOGGER.info("Loaded %d enrolled users", len(enrolled_users))
    if not enrolled_users:
        LOGGER.warning("No enrolled users found; valid faces will be labeled Unknown")

    services.update(
        {
            "embedding_service": FaceEmbeddingService(device=detector.device),
            "recognition_service": FaceRecognitionService(threshold=settings.recognition_distance_threshold),
            "stabilizer": TemporalStabilizer.from_settings(settings),
            "event_logger": EventLogger(settings.event_log_path, settings.event_cooldown_seconds),
            "liveness_service": LivenessService(),
            "enrolled_users": enrolled_users,
        }
    )
    return services


def process_image(
    image_path: Path,
    output_path: Path | None,
    settings: config.AppSettings,
    services: dict,
    *,
    detect_only: bool,
    display: bool,
) -> bool:
    frame = cv2.imread(str(image_path))
    if frame is None:
        LOGGER.error("Could not read image: %s", image_path)
        return False

    if detect_only:
        observations = detect_faces(frame, services["detector"])
        draw_detection_observations(frame, observations)
    else:
        observations = process_frame(
            frame,
            services["detector"],
            services["quality_service"],
            services["embedding_service"],
            services["recognition_service"],
            services["stabilizer"],
            services["liveness_service"],
            services["event_logger"],
            services["enrolled_users"],
            0,
        )
        draw_observations(frame, observations)

    put_lines(
        frame,
        [
            f"Source: {image_path.name}",
            f"Faces: {len(observations)}",
            "Mode: detect only" if detect_only else f"Threshold: {settings.recognition_distance_threshold:.2f}",
        ],
    )
    print_summary(image_path, observations, detect_only=detect_only)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), frame)
        LOGGER.info("Saved annotated image: %s", output_path)
    if display:
        cv2.imshow(f"Campus E-ID Image - {image_path.name}", frame)
        cv2.waitKey(0)
    return True


def print_summary(image_path: Path, observations: list[dict], *, detect_only: bool) -> None:
    if not observations:
        print(f"{image_path.name}: no_face")
        return
    for index, observation in enumerate(observations, start=1):
        probability = float(observation.get("probability") or 0.0)
        if detect_only:
            print(f"{image_path.name}: face {index} detected probability={probability:.3f}")
            continue

        distance = observation.get("distance")
        distance_text = "n/a" if distance is None else f"{float(distance):.3f}"
        user_id = observation.get("user_id")
        name = observation.get("name") or "Unknown"
        label = f"{name} ({user_id})" if user_id else str(name)
        quality = observation.get("quality")
        reason = getattr(quality, "reason", None) or "ok"
        print(
            f"{image_path.name}: face {index} -> {label} "
            f"distance={distance_text} quality={reason} probability={probability:.3f}"
        )


def resolve_image_sources(source: Path) -> list[Path]:
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    if source.is_file() and source.suffix.lower() in IMAGE_EXTENSIONS:
        return [source]
    if source.is_dir():
        return sorted(path for path in source.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)
    return []


def resolve_image_output_path(output_base: Path | None, image_path: Path, *, multiple: bool) -> Path | None:
    if output_base is None:
        return None
    resolved = resolve_output_path(output_base, image_path, multiple=multiple)
    if resolved is None:
        return None
    if resolved.suffix.lower() not in IMAGE_EXTENSIONS:
        return resolved.with_suffix(".jpg")
    return resolved


if __name__ == "__main__":
    raise SystemExit(main())
