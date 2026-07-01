from __future__ import annotations

import socket

from flightpath_video.web_launcher import build_local_url, find_available_port, format_startup_error, write_startup_error


def test_find_available_port_returns_bindable_localhost_port() -> None:
    port = find_available_port()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))


def test_build_local_url_uses_loopback_host_and_port() -> None:
    assert build_local_url(53123) == "http://127.0.0.1:53123"


def test_startup_error_message_is_localized() -> None:
    message = format_startup_error(RuntimeError("boom"))

    assert "本地 Web 服务启动失败" in message
    assert "boom" in message


def test_write_startup_error_creates_parent_directory(tmp_path) -> None:
    log_path = tmp_path / "nested" / "startup.log"

    write_startup_error("启动失败", log_path)

    assert log_path.read_text(encoding="utf-8") == "启动失败\n"
