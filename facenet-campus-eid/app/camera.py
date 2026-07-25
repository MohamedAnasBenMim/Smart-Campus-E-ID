"""OpenCV camera and drawing helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Camera:
    """Small wrapper around cv2.VideoCapture."""

    index: int = 0

    def __post_init__(self) -> None:
        import cv2

        self._cv2 = cv2
        self.capture = cv2.VideoCapture(self.index)
        if not self.capture.isOpened():
            raise RuntimeError(f"Could not open webcam at index {self.index}")

    def read(self):
        """Read one frame, returning (ok, frame)."""

        return self.capture.read()

    def release(self) -> None:
        """Release the webcam."""

        self.capture.release()


def draw_box(frame, box: tuple[int, int, int, int], label: str, color: tuple[int, int, int]) -> None:
    """Draw a labeled bounding box in place."""

    import cv2

    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    text_y = max(20, y1 - 8)
    cv2.putText(frame, label, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)


def put_lines(
    frame,
    lines: list[str],
    *,
    origin: tuple[int, int] = (16, 28),
    color: tuple[int, int, int] = (255, 255, 255),
) -> None:
    """Draw status lines in place."""

    import cv2

    x, y = origin
    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (x, y + index * 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            color,
            2,
            cv2.LINE_AA,
        )

