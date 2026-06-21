from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


REAL_LOGS = [
    Path(r"C:\Users\king\Documents\Mission Planner\logs\QUADROTOR\1\2026-06-06 14-32-42.bin"),
    Path(r"C:\Users\king\Documents\Mission Planner\logs\QUADROTOR\1\2026-06-06 14-32-32.bin"),
]
