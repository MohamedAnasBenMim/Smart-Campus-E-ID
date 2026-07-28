"""Embedding comparison and lightweight recognition stabilization."""

from __future__ import annotations

import math
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.config import (
    AppSettings,
    RECOGNITION_DISTANCE_THRESHOLD,
    TRACKING_CONFIRMATION_COUNT,
    TRACKING_HISTORY_LENGTH,
    TRACKING_STALE_FRAMES,
)
from app.storage_service import StoredUser


@dataclass(frozen=True)
class RecognitionResult:
    """Identity decision for one face embedding."""

    user_id: str | None
    name: str
    role: str | None
    distance: float | None
    known: bool
    metadata: dict[str, Any] = field(default_factory=dict)


def l2_normalize(embedding: np.ndarray) -> np.ndarray:
    """Return a unit-length copy of an embedding."""

    array = np.asarray(embedding, dtype=np.float32)
    norm = float(np.linalg.norm(array))
    if norm == 0.0:
        raise ValueError("cannot normalize a zero vector")
    return array / norm


def euclidean_distance(left: np.ndarray, right: np.ndarray) -> float:
    """Compute Euclidean distance between two embeddings."""

    return float(np.linalg.norm(np.asarray(left, dtype=np.float32) - np.asarray(right, dtype=np.float32)))


class FaceRecognitionService:
    """Find the nearest enrolled sample embedding and apply the Unknown threshold."""

    def __init__(self, threshold: float = RECOGNITION_DISTANCE_THRESHOLD) -> None:
        self.threshold = threshold

    def recognize(self, query_embedding: np.ndarray, enrolled_users: dict[str, StoredUser]) -> RecognitionResult:
        """Return the best match or Unknown when the database is empty or too distant."""

        if not enrolled_users:
            return RecognitionResult(user_id=None, name="Unknown", role=None, distance=None, known=False)

        best_user: StoredUser | None = None
        best_distance = math.inf
        for user in enrolled_users.values():
            distance = nearest_embedding_distance(query_embedding, user.sample_embeddings)
            if distance < best_distance:
                best_user = user
                best_distance = distance

        if best_user is None or best_distance > self.threshold:
            return RecognitionResult(
                user_id=None,
                name="Unknown",
                role=None,
                distance=best_distance if math.isfinite(best_distance) else None,
                known=False,
            )

        return RecognitionResult(
            user_id=best_user.user_id,
            name=str(best_user.metadata.get("name") or best_user.user_id),
            role=best_user.metadata.get("role"),
            distance=best_distance,
            known=True,
            metadata=best_user.metadata,
        )


def nearest_embedding_distance(query_embedding: np.ndarray, enrolled_embeddings: np.ndarray) -> float:
    """Return the closest Euclidean distance from a query to one or more enrollment embeddings."""

    query = np.asarray(query_embedding, dtype=np.float32)
    enrolled = np.asarray(enrolled_embeddings, dtype=np.float32)
    if enrolled.ndim == 1:
        return euclidean_distance(query, enrolled)
    if enrolled.ndim != 2:
        raise ValueError(f"enrolled embeddings must be 1D or 2D, got {enrolled.ndim}D")
    distances = np.linalg.norm(enrolled - query.reshape(1, -1), axis=1)
    return float(np.min(distances))


@dataclass
class _Track:
    track_id: int
    box: tuple[int, int, int, int]
    last_seen_frame: int
    history: deque[str]
    last_observation: dict[str, Any]
    confirmed_label: str | None = None


class TemporalStabilizer:
    """Simple centroid-based identity smoothing for webcam display."""

    def __init__(
        self,
        history_length: int = TRACKING_HISTORY_LENGTH,
        confirmation_count: int = TRACKING_CONFIRMATION_COUNT,
        stale_frames: int = TRACKING_STALE_FRAMES,
    ) -> None:
        self.history_length = history_length
        self.confirmation_count = confirmation_count
        self.stale_frames = stale_frames
        self._tracks: dict[int, _Track] = {}
        self._next_track_id = 1

    @classmethod
    def from_settings(cls, settings: AppSettings) -> "TemporalStabilizer":
        return cls(
            history_length=settings.tracking_history_length,
            confirmation_count=settings.tracking_confirmation_count,
            stale_frames=settings.tracking_stale_frames,
        )

    def update(self, observations: list[dict[str, Any]], frame_index: int) -> list[dict[str, Any]]:
        """Attach stable display labels to current face observations."""

        matched_track_ids: set[int] = set()
        stabilized: list[dict[str, Any]] = []

        for observation in observations:
            box = _as_box(observation["box"])
            track = self._match_track(box, matched_track_ids)
            label = _identity_label(observation)

            if track is None:
                track = _Track(
                    track_id=self._next_track_id,
                    box=box,
                    last_seen_frame=frame_index,
                    history=deque(maxlen=self.history_length),
                    last_observation=observation,
                )
                self._tracks[track.track_id] = track
                self._next_track_id += 1

            matched_track_ids.add(track.track_id)
            track.box = box
            track.last_seen_frame = frame_index
            track.last_observation = observation
            track.history.append(label)

            counts = Counter(track.history)
            most_common_label, count = counts.most_common(1)[0]
            if count >= self.confirmation_count:
                track.confirmed_label = most_common_label

            display = dict(observation)
            display["track_id"] = track.track_id
            display["stable_label"] = track.confirmed_label or label
            display["stable"] = track.confirmed_label is not None
            stabilized.append(display)

        self._drop_stale_tracks(frame_index)
        return stabilized

    def _match_track(self, box: tuple[int, int, int, int], used_track_ids: set[int]) -> _Track | None:
        best_track: _Track | None = None
        best_distance = math.inf
        for track in self._tracks.values():
            if track.track_id in used_track_ids:
                continue
            distance = _centroid_distance(box, track.box)
            if distance < best_distance and distance <= _match_radius(box, track.box):
                best_track = track
                best_distance = distance
        return best_track

    def _drop_stale_tracks(self, frame_index: int) -> None:
        stale = [
            track_id
            for track_id, track in self._tracks.items()
            if frame_index - track.last_seen_frame > self.stale_frames
        ]
        for track_id in stale:
            del self._tracks[track_id]


def _identity_label(observation: dict[str, Any]) -> str:
    if observation.get("known") and observation.get("user_id"):
        return str(observation["user_id"])
    return "Unknown"


def _as_box(box: Any) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    return int(x1), int(y1), int(x2), int(y2)


def _centroid_distance(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> float:
    left_cx = (left[0] + left[2]) / 2.0
    left_cy = (left[1] + left[3]) / 2.0
    right_cx = (right[0] + right[2]) / 2.0
    right_cy = (right[1] + right[3]) / 2.0
    return math.hypot(left_cx - right_cx, left_cy - right_cy)


def _match_radius(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> float:
    width = max(abs(left[2] - left[0]), abs(right[2] - right[0]))
    height = max(abs(left[3] - left[1]), abs(right[3] - right[1]))
    return max(50.0, 0.6 * math.hypot(width, height))
