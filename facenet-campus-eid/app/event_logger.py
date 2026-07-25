"""JSON Lines event logging with cooldowns."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import EVENT_COOLDOWN_SECONDS, EVENT_LOG_PATH

LOGGER = logging.getLogger(__name__)


class EventLogger:
    """Append access events locally without logging the same decision every frame."""

    def __init__(
        self,
        event_log_path: Path = EVENT_LOG_PATH,
        cooldown_seconds: float = EVENT_COOLDOWN_SECONDS,
    ) -> None:
        self.event_log_path = event_log_path
        self.cooldown_seconds = cooldown_seconds
        self._last_logged_at: dict[str, float] = {}
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event_type: str, decision: str, **fields: Any) -> bool:
        """Write one event unless its cooldown key is still cooling down."""

        key = self._cooldown_key(event_type, fields)
        now = time.monotonic()
        if now - self._last_logged_at.get(key, 0.0) < self.cooldown_seconds:
            return False

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "decision": decision,
            **fields,
        }
        with self.event_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        self._last_logged_at[key] = now
        LOGGER.info("Logged %s event: %s", event_type, decision)
        return True

    @staticmethod
    def _cooldown_key(event_type: str, fields: dict[str, Any]) -> str:
        identity = fields.get("user_id") or fields.get("name") or "unknown"
        return f"{event_type}:{identity}"

