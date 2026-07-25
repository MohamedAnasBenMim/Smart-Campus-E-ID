"""Central configuration for the FaceNet campus E-ID prototype."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
ENROLLED_FACES_DIR = DATA_DIR / "enrolled_faces"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
EVENTS_DIR = DATA_DIR / "events"
EVENT_LOG_PATH = EVENTS_DIR / "access_events.jsonl"

CAMERA_INDEX = 0

DETECTION_CONFIDENCE_THRESHOLD = 0.90
RECOGNITION_DISTANCE_THRESHOLD = 0.90

MIN_FACE_SIZE = 80
BLUR_THRESHOLD = 40.0
MIN_BRIGHTNESS = 40.0
MAX_BRIGHTNESS = 215.0
FACE_BORDER_MARGIN_RATIO = 0.04

ENROLLMENT_SAMPLES = 10
CAPTURE_DELAY_SECONDS = 1.2

EVENT_COOLDOWN_SECONDS = 8.0
PROCESS_EVERY_N_FRAMES = 3
TRACKING_HISTORY_LENGTH = 8
TRACKING_CONFIRMATION_COUNT = 3
TRACKING_STALE_FRAMES = 20

DETECTION_MAX_WIDTH = 640

FACENET_IMAGE_SIZE = 160
EMBEDDING_DIMENSION = 512
EMBEDDING_MODEL_NAME = "InceptionResnetV1-VGGFace2"


@dataclass(frozen=True)
class AppSettings:
    """Runtime settings collected in one object for easy dependency injection."""

    project_root: Path = PROJECT_ROOT
    enrolled_faces_dir: Path = ENROLLED_FACES_DIR
    embeddings_dir: Path = EMBEDDINGS_DIR
    events_dir: Path = EVENTS_DIR
    event_log_path: Path = EVENT_LOG_PATH
    camera_index: int = CAMERA_INDEX
    detection_confidence_threshold: float = DETECTION_CONFIDENCE_THRESHOLD
    recognition_distance_threshold: float = RECOGNITION_DISTANCE_THRESHOLD
    min_face_size: int = MIN_FACE_SIZE
    blur_threshold: float = BLUR_THRESHOLD
    min_brightness: float = MIN_BRIGHTNESS
    max_brightness: float = MAX_BRIGHTNESS
    face_border_margin_ratio: float = FACE_BORDER_MARGIN_RATIO
    enrollment_samples: int = ENROLLMENT_SAMPLES
    capture_delay_seconds: float = CAPTURE_DELAY_SECONDS
    event_cooldown_seconds: float = EVENT_COOLDOWN_SECONDS
    process_every_n_frames: int = PROCESS_EVERY_N_FRAMES
    tracking_history_length: int = TRACKING_HISTORY_LENGTH
    tracking_confirmation_count: int = TRACKING_CONFIRMATION_COUNT
    tracking_stale_frames: int = TRACKING_STALE_FRAMES
    detection_max_width: int = DETECTION_MAX_WIDTH
    facenet_image_size: int = FACENET_IMAGE_SIZE
    embedding_dimension: int = EMBEDDING_DIMENSION
    embedding_model_name: str = EMBEDDING_MODEL_NAME


def ensure_data_directories(settings: AppSettings | None = None) -> None:
    """Create local data directories if they do not exist."""

    settings = settings or AppSettings()
    settings.enrolled_faces_dir.mkdir(parents=True, exist_ok=True)
    settings.embeddings_dir.mkdir(parents=True, exist_ok=True)
    settings.events_dir.mkdir(parents=True, exist_ok=True)

