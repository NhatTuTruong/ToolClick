"""Chạy job scrape từ UI / CLI — build env và lệnh main.py."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

try:
    from toolclick_paths import is_frozen, writable_root
except ImportError:
    def is_frozen() -> bool:
        return getattr(sys, "frozen", False)

    def writable_root() -> Path:
        return Path(__file__).resolve().parent.parent


def project_root() -> Path:
    if is_frozen():
        return writable_root()
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = project_root()


@dataclass
class JobSettings:
    keywords: list[str]
    headed: bool = True
    output_dir: str = "output"
    export_format: str = "xlsx"
    debug: bool = False
    click_organic: bool = False
    max_organic: int = 5
    organic_dwell_ms: int | None = None
    click_sponsored_test: bool = False
    max_sponsored: int = 3
    sponsored_dwell_ms: int | None = None
    serp_repeat: int | None = None
    allowed_domains: list[str] | None = None
    skip_domains: list[str] | None = None
    proxy_list: list[str] | None = None
    proxy_rotate_mode: str = "keyword"
    proxy_persist_profile: bool = True
    proxy_warmup_all: bool = False
    license_server_url: str = "http://127.0.0.1:8000"
    license_key: str = ""
    license_api_secret: str = ""
    # env
    google_locale: str = "vi-VN"
    search_delay_ms: int = 2500
    browser_channel: str = "chrome"
    use_persistent_profile: bool = True
    user_data_dir: str = "browser-profile"
    captcha_wait_sec: int = 300
    organic_click_delay_ms: int = 800
    enable_sponsored_click_test: bool = False
    sponsored_dwell_ms_env: int = 2000
    sponsored_click_delay_ms: int = 800
    organic_dwell_ms_env: int = 2000

    def to_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["HEADLESS"] = "false" if self.headed else "true"
        env["GOOGLE_LOCALE"] = self.google_locale
        env["SEARCH_DELAY_MS"] = str(self.search_delay_ms)
        env["BROWSER_CHANNEL"] = self.browser_channel
        env["USE_PERSISTENT_PROFILE"] = "true" if self.use_persistent_profile else "false"
        env["USER_DATA_DIR"] = self.user_data_dir
        env["CAPTCHA_WAIT_SEC"] = str(self.captcha_wait_sec)
        env["ORGANIC_DWELL_MS"] = str(self.organic_dwell_ms_env)
        env["ORGANIC_CLICK_DELAY_MS"] = str(self.organic_click_delay_ms)
        env["ENABLE_SPONSORED_CLICK_TEST"] = (
            "true" if self.enable_sponsored_click_test else "false"
        )
        env["SPONSORED_DWELL_MS"] = str(self.sponsored_dwell_ms_env)
        env["SPONSORED_CLICK_DELAY_MS"] = str(self.sponsored_click_delay_ms)
        if self.serp_repeat is not None:
            env["SERP_REPEAT_COUNT"] = str(self.serp_repeat)
        env["ALLOWED_CLICK_DOMAINS"] = (
            ",".join(self.allowed_domains) if self.allowed_domains else ""
        )
        env["SKIP_CLICK_DOMAINS"] = (
            ",".join(self.skip_domains) if self.skip_domains else ""
        )
        env["PROXY_LIST"] = "|".join(self.proxy_list) if self.proxy_list else ""
        env["PROXY_ROTATE_MODE"] = self.proxy_rotate_mode
        env["PROXY_PERSIST_PROFILE"] = "true" if self.proxy_persist_profile else "false"
        env["PROXY_WARMUP_ALL"] = "true" if self.proxy_warmup_all else "false"
        env["LICENSE_SERVER_URL"] = self.license_server_url or ""
        env["LICENSE_KEY"] = self.license_key or ""
        env["LICENSE_API_SECRET"] = self.license_api_secret or ""
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def build_argv(self) -> list[str]:
        argv = [resolve_python_executable()]
        if not is_frozen():
            argv.append(str(project_root() / "main.py"))
        else:
            argv.append("--toolclick-main")
        argv.extend(
            [
            "-k",
            *self.keywords,
            "-o",
            self.output_dir,
            "--format",
            self.export_format,
            ]
        )
        if self.headed:
            argv.append("--headed")
        if self.debug:
            argv.append("--debug")
        if self.click_organic:
            argv.extend(["--click-organic", "--max-organic", str(self.max_organic)])
            if self.organic_dwell_ms is not None:
                argv.extend(["--organic-dwell-ms", str(self.organic_dwell_ms)])
        if self.click_sponsored_test:
            argv.extend(["--click-sponsored-test", "--max-sponsored", str(self.max_sponsored)])
            if self.sponsored_dwell_ms is not None:
                argv.extend(["--sponsored-dwell-ms", str(self.sponsored_dwell_ms)])
            if self.serp_repeat is not None:
                argv.extend(["--serp-repeat", str(self.serp_repeat)])
            if self.allowed_domains:
                argv.extend(["--allowed-domains", *self.allowed_domains])
            if self.skip_domains:
                argv.extend(["--skip-domains", *self.skip_domains])
        return argv


def resolve_python_executable() -> str:
    if is_frozen():
        return sys.executable
    root = project_root()
    if sys.platform == "win32":
        venv_py = root / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = root / ".venv" / "bin" / "python"
    if venv_py.is_file():
        return str(venv_py)
    return sys.executable


def launch_browser_window(settings: JobSettings) -> None:
    """Mo Chrome headed trong cua so console rieng (Windows)."""
    env = settings.to_env()
    env["HEADLESS"] = "false"
    env["PYTHONIOENCODING"] = "utf-8"

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]

    exe = resolve_python_executable()
    if is_frozen():
        cmd = [exe, "--open-browser"]
    else:
        cmd = [exe, str(project_root() / "open_browser.py")]

    subprocess.Popen(
        cmd,
        cwd=str(project_root()),
        env=env,
        creationflags=creationflags,
    )


def stream_job(settings: JobSettings) -> Iterator[str]:
    """Yield từng dòng stdout/stderr của main.py."""
    if not settings.keywords:
        yield "Lỗi: chưa có từ khóa.\n"
        return

    argv = settings.build_argv()
    yield f"$ {' '.join(argv)}\n\n"

    proc = subprocess.Popen(
        argv,
        cwd=str(project_root()),
        env=settings.to_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        yield line
    code = proc.wait()
    yield f"\n--- Kết thúc (exit code {code}) ---\n"
