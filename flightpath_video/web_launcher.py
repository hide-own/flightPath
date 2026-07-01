from __future__ import annotations

import socket
import sys
import webbrowser
from pathlib import Path


LOCAL_HOST = "127.0.0.1"


def find_available_port(host: str = LOCAL_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def build_local_url(port: int, host: str = LOCAL_HOST) -> str:
    return f"http://{host}:{port}"


def format_startup_error(exc: BaseException) -> str:
    return f"本地 Web 服务启动失败：{exc}"


def write_startup_error(message: str, log_path: Path | None = None) -> Path:
    target = log_path or Path("cache") / "startup_error.log"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(message + "\n", encoding="utf-8")
    return target


def main(open_browser: bool = True) -> None:
    try:
        import uvicorn

        port = find_available_port()
        url = build_local_url(port)
        if open_browser:
            webbrowser.open(url)
        uvicorn.run("flightpath_video.local_api:app", host=LOCAL_HOST, port=port, log_level="info")
    except Exception as exc:
        message = format_startup_error(exc)
        log_path = write_startup_error(message)
        print(f"{message}\n错误日志：{log_path}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
