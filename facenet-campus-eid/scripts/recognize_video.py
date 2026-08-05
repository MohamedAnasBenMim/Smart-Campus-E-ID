#!/usr/bin/env python
"""Detect and recognize faces from recorded classroom videos."""

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
from app.camera import draw_box, put_lines
from app.embedding_service import FaceEmbeddingService
from app.event_logger import EventLogger
from app.face_detector import MTCNNFaceDetector
from app.liveness_service import LivenessService
from app.quality_service import FaceQualityService
from app.recognition_service import FaceRecognitionService, TemporalStabilizer
from app.storage_service import StorageService
from recognize_webcam import draw_observations, process_frame

LOGGER = logging.getLogger(__name__)
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run face detection/recognition on video files.")
    parser.add_argument(
        "--source",
        default="videos",
        help="Video file or directory of videos. Defaults to the project's videos/ folder.",
    )
    parser.add_argument(
        "--output",
        help="Optional annotated output video file or output directory when processing a directory.",
    )
    parser.add_argument("--threshold", type=float, default=config.RECOGNITION_DISTANCE_THRESHOLD)
    parser.add_argument("--min-face-size", type=int, default=config.MIN_FACE_SIZE)
    parser.add_argument("--process-every", type=int, default=config.PROCESS_EVERY_N_FRAMES)
    parser.add_argument("--max-frames", type=int, help="Stop after this many frames per video.")
    parser.add_argument("--detect-only", action="store_true", help="Only draw detected faces; skip embeddings.")
    parser.add_argument("--no-display", action="store_true", help="Process without opening an OpenCV window.")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args()
    if args.process_every < 1:
        raise SystemExit("--process-every must be at least 1")

    settings = config.AppSettings(
        recognition_distance_threshold=args.threshold,
        min_face_size=args.min_face_size,
        process_every_n_frames=args.process_every,
    )
    config.ensure_data_directories(settings)

    source_paths = resolve_sources(PROJECT_ROOT / args.source)
    if not source_paths:
        raise SystemExit(f"No videos found at {args.source}")

    output_base = Path(args.output) if args.output else None
    services = build_services(settings, detect_only=args.detect_only)

    exit_code = 0
    for source_path in source_paths:
        output_path = resolve_output_path(output_base, source_path, multiple=len(source_paths) > 1)
        ok = process_video(
            source_path,
            output_path,
            settings,
            services,
            display=not args.no_display,
            detect_only=args.detect_only,
            max_frames=args.max_frames,
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
        LOGGER.info("Video detection-only mode ready on %s", detector.device)
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


def process_video(
    source_path: Path,
    output_path: Path | None,
    settings: config.AppSettings,
    services: dict,
    *,
    display: bool,
    detect_only: bool,
    max_frames: int | None,
) -> bool:
    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        LOGGER.error("Could not open video: %s", source_path)
        return False

    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    LOGGER.info("Processing %s (%dx%d, %.2f FPS, %d frames)", source_path, width, height, fps, total_frames)

    writer = create_writer(output_path, fps, width, height)
    frame_index = 0
    display_observations: list[dict] = []
    window_name = f"Campus E-ID Video - {source_path.name}"
    delay_ms = max(1, int(round(1000.0 / fps)))

    try:
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                break
            if max_frames is not None and frame_index >= max_frames:
                break

            if frame_index % settings.process_every_n_frames == 0:
                if detect_only:
                    display_observations = detect_faces(frame, services["detector"])
                else:
                    display_observations = process_frame(
                        frame,
                        services["detector"],
                        services["quality_service"],
                        services["embedding_service"],
                        services["recognition_service"],
                        services["stabilizer"],
                        services["liveness_service"],
                        services["event_logger"],
                        services["enrolled_users"],
                        frame_index,
                    )

            if detect_only:
                draw_detection_observations(frame, display_observations)
            else:
                draw_observations(frame, display_observations)

            put_lines(
                frame,
                [
                    f"Source: {source_path.name}",
                    f"Frame: {frame_index + 1}/{total_frames if total_frames else '?'}",
                    f"Faces: {len(display_observations)}",
                    "Mode: detect only" if detect_only else f"Threshold: {settings.recognition_distance_threshold:.2f}",
                    "Q: quit",
                ],
            )

            if writer is not None:
                writer.write(frame)
            if display:
                cv2.imshow(window_name, frame)
                if cv2.waitKey(delay_ms) & 0xFF == ord("q"):
                    return True
            frame_index += 1
    finally:
        capture.release()
        if writer is not None:
            writer.release()
        if display:
            cv2.destroyWindow(window_name)

    LOGGER.info("Finished %s after %d frames", source_path.name, frame_index)
    if output_path is not None:
        LOGGER.info("Saved annotated video: %s", output_path)
    return True


def detect_faces(frame, detector: MTCNNFaceDetector) -> list[dict]:
    detections = detector.detect_bgr(frame)
    return [
        {
            "box": detection.box,
            "probability": detection.probability,
        }
        for detection in detections
    ]


def draw_detection_observations(frame, observations: list[dict]) -> None:
    for observation in observations:
        label = f"face {float(observation['probability']):.2f}"
        draw_box(frame, observation["box"], label, (0, 200, 255))


def create_writer(output_path: Path | None, fps: float, width: int, height: int):
    if output_path is None:
        return None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not create output video: {output_path}")
    return writer


def resolve_sources(source: Path) -> list[Path]:
    if not source.is_absolute():
        source = PROJECT_ROOT / source
    if source.is_file():
        return [source]
    if source.is_dir():
        return sorted(path for path in source.iterdir() if path.suffix.lower() in VIDEO_EXTENSIONS)
    return []


def resolve_output_path(output_base: Path | None, source_path: Path, *, multiple: bool) -> Path | None:
    if output_base is None:
        return None
    if not output_base.is_absolute():
        output_base = PROJECT_ROOT / output_base
    if multiple or output_base.suffix == "":
        return output_base / f"{source_path.stem}_recognized.mp4"
    return output_base


if __name__ == "__main__":
    raise SystemExit(main())
