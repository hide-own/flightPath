from __future__ import annotations

import sys
import traceback
from pathlib import Path
from tkinter import Tk, messagebox


ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "launch_error.log"


def show_error(message: str) -> None:
    LOG_PATH.write_text(message, encoding="utf-8")
    root = Tk()
    root.withdraw()
    messagebox.showerror("飞行日志轨迹视频生成工具", message)
    root.destroy()


def main() -> int:
    try:
        sys.path.insert(0, str(ROOT))
        from flightpath_video.app import main as app_main

        return app_main()
    except ModuleNotFoundError as exc:
        show_error(f"无法启动：缺少运行依赖 {exc.name}。\n请先安装 requirements.txt 中的依赖。")
        return 1
    except Exception:
        show_error(f"无法启动应用。\n\n{traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
