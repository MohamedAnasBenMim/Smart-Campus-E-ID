"""MTCNN-based face detection and alignment."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from app.config import (
    DETECTION_CONFIDENCE_THRESHOLD,
    DETECTION_MAX_WIDTH,
    FACENET_IMAGE_SIZE,
)
from app.embedding_service import FaceEmbeddingService

LOGGER = logging.getLogger(__name__)


class FaceDetectionError(RuntimeError):
    """Raised when MTCNN cannot be initialized or used."""


@dataclass(frozen=True)
class FaceDetection:
    """One detected face and its aligned FaceNet tensor."""

    box: tuple[int, int, int, int]
    probability: float
    aligned_face: Any | None


class MTCNNFaceDetector:
    """Detect faces in BGR OpenCV frames and align them for FaceNet."""

    def __init__(
        self,
        confidence_threshold: float = DETECTION_CONFIDENCE_THRESHOLD,
        image_size: int = FACENET_IMAGE_SIZE,
        device: str | None = None,
        max_detection_width: int = DETECTION_MAX_WIDTH,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.image_size = image_size
        self.device = device or FaceEmbeddingService.select_device()
        self.max_detection_width = max_detection_width
        self.mtcnn = self._load_mtcnn()
        LOGGER.info("MTCNN detector ready on %s", self.device)

    def detect_bgr(self, frame_bgr: np.ndarray) -> list[FaceDetection]:
        """Detect faces in an OpenCV BGR image."""

        if frame_bgr is None or frame_bgr.size == 0:
            return []
        rgb = self.bgr_to_rgb(frame_bgr)
        return self.detect_rgb(rgb)

    def detect_rgb(self, image_rgb: np.ndarray) -> list[FaceDetection]:
        """Detect faces in an RGB image and return aligned tensors."""

        if image_rgb is None or image_rgb.size == 0:
            return []

        full_image = Image.fromarray(image_rgb)
        detection_image, scale = self._resize_for_detection(image_rgb)
        detection_pil = Image.fromarray(detection_image)

        try:
            boxes, probabilities = self.mtcnn.detect(detection_pil)
        except Exception as exc:
            raise FaceDetectionError(f"MTCNN detection failed: {exc}") from exc

        if boxes is None or probabilities is None:
            return []

        scaled_boxes: list[tuple[int, int, int, int]] = []
        filtered_probabilities: list[float] = []
        for box, probability in zip(boxes, probabilities):
            if probability is None or float(probability) < self.confidence_threshold:
                continue
            x1, y1, x2, y2 = (np.asarray(box, dtype=np.float32) / scale).tolist()
            scaled_boxes.append((int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))))
            filtered_probabilities.append(float(probability))

        if not scaled_boxes:
            return []

        aligned_faces = self._extract_aligned_faces(full_image, scaled_boxes)
        detections: list[FaceDetection] = []
        for index, (box, probability) in enumerate(zip(scaled_boxes, filtered_probabilities)):
            aligned_face = aligned_faces[index] if index < len(aligned_faces) else None
            detections.append(FaceDetection(box=box, probability=probability, aligned_face=aligned_face))
        return detections

    @staticmethod
    def bgr_to_rgb(frame_bgr: np.ndarray) -> np.ndarray:
        """Convert an OpenCV BGR frame to RGB without depending on cv2 at import time."""

        return frame_bgr[:, :, ::-1].copy()

    def _extract_aligned_faces(self, full_image: Image.Image, boxes: list[tuple[int, int, int, int]]) -> list[Any]:
        try:
            aligned = self.mtcnn.extract(full_image, np.asarray(boxes, dtype=np.float32), save_path=None)
        except Exception as exc:
            raise FaceDetectionError(f"MTCNN alignment failed: {exc}") from exc

        if aligned is None:
            return []
        try:
            import torch

            if torch.is_tensor(aligned):
                if aligned.ndim == 3:
                    return [aligned]
                return [face for face in aligned]
        except Exception:
            pass
        if isinstance(aligned, (list, tuple)):
            return list(aligned)
        return [aligned]

    def _resize_for_detection(self, image_rgb: np.ndarray) -> tuple[np.ndarray, float]:
        height, width = image_rgb.shape[:2]
        if width <= self.max_detection_width:
            return image_rgb, 1.0
        scale = self.max_detection_width / float(width)
        new_size = (self.max_detection_width, int(round(height * scale)))
        try:
            import cv2

            return cv2.resize(image_rgb, new_size, interpolation=cv2.INTER_AREA), scale
        except Exception:
            return image_rgb, 1.0

    def _load_mtcnn(self) -> Any:
        try:
            from facenet_pytorch import MTCNN

            return MTCNN(
                image_size=self.image_size,
                margin=20,
                keep_all=True,
                post_process=True,
                device=self.device,
            )
        except Exception as exc:
            raise FaceDetectionError(
                "Could not initialize facenet-pytorch MTCNN. Install requirements first."
            ) from exc

