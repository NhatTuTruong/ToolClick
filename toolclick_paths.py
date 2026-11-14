"""Đường dẫn khi chạy source vs bản đóng gói PyInstaller."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def writable_root() -> Path:
    """Thư mục ghi .env, output, browser-profile (cạnh file .exe)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_root() -> Path:
    """Mã nguồn đóng gói (desktop_app.py, src/, main.py)."""
    if is_frozen():
        exe_dir = Path(sys.executable).resolve().parent
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            p = Path(meipass)
            if (p / "desktop_app.py").is_file() or (p / "main.py").is_file():
                return p
        internal = exe_dir / "_internal"
        if (internal / "desktop_app.py").is_file() or (internal / "main.py").is_file():
            return internal
        return exe_dir
    return Path(__file__).resolve().parent


def ensure_streamlit_config() -> None:
    """Cấu hình Streamlit cho bản .exe (tắt developmentMode)."""
    cfg_dir = writable_root() / ".streamlit"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = cfg_dir / "config.toml"
    if cfg.is_file():
        return
    cfg.write_text(
        """[global]
developmentMode = false

[server]
headless = true
port = 8501
address = "localhost"

[browser]
gatherUsageStats = false
""",
        encoding="utf-8",
    )


def ensure_runtime_layout() -> None:
    """Tạo .env mẫu và thêm resource_root vào sys.path."""
    root = resource_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    data = writable_root()
    env_file = data / ".env"
    if env_file.is_file():
        return
    for name in ("config.example.env", ".env.example"):
        example = root / name
        if example.is_file():
            env_file.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            return
    example = data / "config.example.env"
    if example.is_file():
        env_file.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
