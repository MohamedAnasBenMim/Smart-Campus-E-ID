"""Convenience entrypoint for the local FaceNet campus E-ID prototype."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Campus E-ID FaceNet prototype")
    parser.add_argument("command", choices=["recognize", "test-model"], help="Command to run")
    args, extra = parser.parse_known_args()

    script = {
        "recognize": PROJECT_ROOT / "scripts" / "recognize_webcam.py",
        "test-model": PROJECT_ROOT / "scripts" / "test_model.py",
    }[args.command]
    return subprocess.call([sys.executable, str(script), *extra])


if __name__ == "__main__":
    raise SystemExit(main())

