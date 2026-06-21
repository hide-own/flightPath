from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from flightpath_video.app import MainWindow


def grab(window: MainWindow, path: Path) -> None:
    QApplication.processEvents()
    pixmap = window.grab()
    path.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(str(path))


def main() -> int:
    suffix = os.environ.get("FLIGHTPATH_SCREENSHOT_SUFFIX", "default")
    out_dir = ROOT / "artifacts" / "acceptance" / "screenshots" / suffix
    log_path = Path(r"C:\Users\king\Documents\Mission Planner\logs\QUADROTOR\1\2026-06-06 14-32-42.bin")

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    size = os.environ.get("FLIGHTPATH_SCREENSHOT_SIZE")
    if size and "x" in size:
        width, height = size.lower().split("x", 1)
        window.resize(int(width), int(height))
    window.show()
    grab(window, out_dir / "01_initial.png")

    window.log_path_edit.setText(str(log_path))
    window.output_path_edit.setText(str(ROOT / "artifacts" / "acceptance" / "ui_sample.mp4"))
    window.parse_current_log()
    grab(window, out_dir / "02_parsing_complete.png")

    window._set_busy(True)
    window.progress_bar.setValue(42)
    window._set_status("状态：正在渲染 30s / 71s", "working")
    grab(window, out_dir / "03_rendering.png")

    window._set_busy(False)
    window.progress_bar.setValue(0)
    window._set_status("状态：失败 地图下载失败", "error")
    grab(window, out_dir / "04_failure.png")

    window.progress_bar.setValue(100)
    window._set_status("状态：生成完成 artifacts/acceptance/ui_sample.mp4", "success")
    grab(window, out_dir / "05_completed.png")

    window.close()
    app.processEvents()
    print(f"captured screenshots in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
