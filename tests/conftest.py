from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


REAL_LOGS = [
    Path(r"C:\Users\king\Documents\Mission Planner\logs\QUADROTOR\1\2026-06-06 14-32-42.bin"),
    Path(r"C:\Users\king\Documents\Mission Planner\logs\QUADROTOR\1\2026-06-06 14-32-32.bin"),
]
