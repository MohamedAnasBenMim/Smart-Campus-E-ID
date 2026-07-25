#!/usr/bin/env python
"""Recognize enrolled campus users from a webcam."""

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
from app.camera import Camera, draw_box, put_lines
from app.embedding_service import EmbeddingError, FaceEmbeddingService
from app.event_logger import EventLogger
from app.face_detector import MTCNNFaceDetector
from app.liveness_service import LivenessService
from app.quality_service import FaceQualityService
from app.recognition_service import FaceRecognitionService, TemporalStabilizer
from app.storage_service import StorageService

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run webcam face recognition.")
    parser.add_argument("--camera-index", type=int, default=config.CAMERA_INDEX)
    parser.add_argument("--threshold", type=float, default=config.RECOGNITION_DISTANCE_THRESHOLD)
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args()
    settings = config.AppSettings(
        camera_index=args.camera_index,
        recognition_distance_threshold=args.threshold,
    )
    config.ensure_data_directories(settings)

    storage = StorageService(settings)
    enrolled_users = storage.load_all_embeddings()
    LOGGER.info("Loaded %d enrolled users", len(enrolled_users))
    if not enrolled_users:
        LOGGER.warning("No enrolled users found; all valid faces will be Unknown")

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
    recognition_service = FaceRecognitionService(threshold=settings.recognition_distance_threshold)
    stabilizer = TemporalStabilizer.from_settings(settings)
    event_logger = EventLogger(settings.event_log_path, settings.event_cooldown_seconds)
    liveness_service = LivenessService()

    camera: Camera | None = None
    frame_index = 0
    display_observations: list[dict] = []
    window_name = "Campus E-ID Recognition"

    try:
        camera = Camera(settings.camera_index)
        LOGGER.info("Recognition started on %s", detector.device)
        while True:
            ok, frame = camera.read()
            if not ok or frame is None:
                LOGGER.error("Frame read failure during recognition")
                event_logger.log("camera_error", "frame_read_failure")
                break

            if frame_index % settings.process_every_n_frames == 0:
                display_observations = process_frame(
                    frame,
                    detector,
                    quality_service,
                    embedding_service,
                    recognition_service,
                    stabilizer,
                    liveness_service,
                    event_logger,
                    enrolled_users,
                    frame_index,
                )

            draw_observations(frame, display_observations)
            put_lines(
                frame,
                [
                    f"Users loaded: {len(enrolled_users)}",
                    f"Threshold: {settings.recognition_distance_threshold:.2f}",
                    "Q: quit",
                ],
            )
            cv2.imshow(window_name, frame)
            frame_index += 1
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        return 0
    except KeyboardInterrupt:
        LOGGER.info("Recognition interrupted")
        return 1
    finally:
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()


def process_frame(
    frame,
    detector: MTCNNFaceDetector,
    quality_service: FaceQualityService,
    embedding_service: FaceEmbeddingService,
    recognition_service: FaceRecognitionService,
    stabilizer: TemporalStabilizer,
    liveness_service: LivenessService,
    event_logger: EventLogger,
    enrolled_users: dict,
    frame_index: int,
) -> list[dict]:
    """Run detection, quality, liveness placeholder, embedding, and recognition."""

    observations: list[dict] = []
    detections = detector.detect_bgr(frame)
    for detection in detections:
        quality = quality_service.evaluate_face(frame, detection)
        observation = {
            "box": detection.box,
            "known": False,
            "user_id": None,
            "name": "Unknown",
            "distance": None,
            "quality": quality,
            "probability": detection.probability,
        }
        if not quality.valid:
            observation["name"] = quality.reason or "poor_quality_face"
            event_logger.log("poor_quality_face", "quality_rejected", reason=quality.reason)
            observations.append(observation)
            continue

        liveness = liveness_service.predict(detection.aligned_face)
        if not liveness["is_live"]:
            observation["name"] = "Spoof"
            event_logger.log("spoof_attempt", "liveness_rejected", liveness=liveness)
            observations.append(observation)
            continue

        if detection.aligned_face is None:
            observation["name"] = "alignment_failed"
            observations.append(observation)
            continue

        try:
            embedding = embedding_service.generate_embedding(detection.aligned_face)
            result = recognition_service.recognize(embedding, enrolled_users)
        except EmbeddingError as exc:
            LOGGER.warning("Embedding failed for live face: %s", exc)
            observation["name"] = "embedding_error"
            observations.append(observation)
            continue

        observation.update(
            {
                "known": result.known,
                "user_id": result.user_id,
                "name": result.name,
                "role": result.role,
                "distance": result.distance,
            }
        )
        if result.known:
            event_logger.log(
                "recognized_person",
                "recognition_success",
                user_id=result.user_id,
                name=result.name,
                distance=result.distance,
            )
        else:
            event_logger.log("unknown_person", "recognition_failed", distance=result.distance)
        observations.append(observation)

    return stabilizer.update(observations, frame_index)


def draw_observations(frame, observations: list[dict]) -> None:
    """Draw recognition decisions on a frame."""

    for observation in observations:
        known = bool(observation.get("known"))
        color = (0, 200, 0) if known else (0, 165, 255)
        distance = observation.get("distance")
        distance_text = "n/a" if distance is None else f"{float(distance):.3f}"
        label = f"{observation.get('stable_label') or observation.get('name')} distance={distance_text}"
        if known and observation.get("user_id"):
            label = f"{observation['name']} ({observation['user_id']}) distance={distance_text}"
        draw_box(frame, observation["box"], label, color)


if __name__ == "__main__":
    raise SystemExit(main())

