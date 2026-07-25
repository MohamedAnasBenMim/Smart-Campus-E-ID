"""Placeholder anti-spoofing integration point."""

from __future__ import annotations

from typing import Any


class LivenessService:
    """Future anti-spoofing service boundary."""

    def predict(self, face_image: Any) -> dict[str, bool | float | str | None]:
        """Return a live decision placeholder without pretending to detect spoofs."""

        return {
            "is_live": True,
            "score": None,
            "status": "not_implemented",
        }

