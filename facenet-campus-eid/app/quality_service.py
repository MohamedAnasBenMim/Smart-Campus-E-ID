"""Basic face-quality validation before enrollment and recognition."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from app.config import (
    BLUR_THRESHOLD,
    DETECTION_CONFIDENCE_THRESHOLD,
    FACE_BORDER_MARGIN_RATIO,
    MAX_BRIGHTNESS,
    MIN_BRIGHTNESS,
    MIN_FACE_SIZE,
)
from app.face_detector import FaceDetection


@dataclass(frozen=True)
class QualityResult:
    """Structured quality result for UI and logging."""

    valid: bool
    reason: str | None
    sharpness: float
    brightness: float

    def to_dict(self) -> dict[str, float | bool | str | None]:
        return asdict(self)


class FaceQualityService:
    """Validate simple quality rules for detected faces."""

    def __init__(
        self,
        min_face_size: int = MIN_FACE_SIZE,
        confidence_threshold: float = DETECTION_CONFIDENCE_THRESHOLD,
        blur_threshold: float = BLUR_THRESHOLD,
        min_brightness: float = MIN_BRIGHTNESS,
        max_brightness: float = MAX_BRIGHTNESS,
        border_margin_ratio: float = FACE_BORDER_MARGIN_RATIO,
    ) -> None:
        self.min_face_size = min_face_size
        self.confidence_threshold = confidence_threshold
        self.blur_threshold = blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.border_margin_ratio = border_margin_ratio

    def evaluate(
        self,
        frame_bgr: np.ndarray,
        detections: list[FaceDetection],
        *,
        require_single_face: bool = True,
    ) -> QualityResult:
        """Validate a frame-level face-detection result."""

        sharpness = self._sharpness(frame_bgr)
        brightness = self._brightness(frame_bgr)

        if not detections:
            return QualityResult(False, "no_face", sharpness, brightness)
        if require_single_face and len(detections) != 1:
            return QualityResult(False, "multiple_faces", sharpness, brightness)

        return self.evaluate_face(frame_bgr, detections[0], sharpness=sharpness, brightness=brightness)

    def evaluate_face(
        self,
        frame_bgr: np.ndarray,
        detection: FaceDetection,
        *,
        sharpness: float | None = None,
        brightness: float | None = None,
    ) -> QualityResult:
        """Validate one detected face."""

        sharpness = self._sharpness(frame_bgr) if sharpness is None else sharpness
        brightness = self._brightness(frame_bgr) if brightness is None else brightness
        x1, y1, x2, y2 = detection.box
        width = max(0, x2 - x1)
        height = max(0, y2 - y1)
        frame_height, frame_width = frame_bgr.shape[:2]

        if detection.probability < self.confidence_threshold:
            return QualityResult(False, "low_detection_confidence", sharpness, brightness)
        if min(width, height) < self.min_face_size:
            return QualityResult(False, "face_too_small", sharpness, brightness)
        if sharpness < self.blur_threshold:
            return QualityResult(False, "image_too_blurry", sharpness, brightness)
        if brightness < self.min_brightness:
            return QualityResult(False, "image_too_dark", sharpness, brightness)
        if brightness > self.max_brightness:
            return QualityResult(False, "image_too_bright", sharpness, brightness)
        if self._near_border(detection.box, frame_width, frame_height):
            return QualityResult(False, "face_near_border", sharpness, brightness)
        return QualityResult(True, None, sharpness, brightness)

    def _near_border(self, box: tuple[int, int, int, int], frame_width: int, frame_height: int) -> bool:
        margin_x = frame_width * self.border_margin_ratio
        margin_y = frame_height * self.border_margin_ratio
        x1, y1, x2, y2 = box
        return x1 < margin_x or y1 < margin_y or x2 > frame_width - margin_x or y2 > frame_height - margin_y

    @staticmethod
    def _brightness(frame_bgr: np.ndarray) -> float:
        gray = _to_gray(frame_bgr)
        return float(np.mean(gray))

    @staticmethod
    def _sharpness(frame_bgr: np.ndarray) -> float:
        gray = _to_gray(frame_bgr)
        try:
            import cv2

            return float(cv2.Laplacian(gray, cv2.CV_64F).var())
        except Exception:
            return 0.0


def _to_gray(frame_bgr: np.ndarray) -> np.ndarray:
    try:
        import cv2

        return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    except Exception:
        return np.mean(frame_bgr, axis=2).astype(np.uint8)

