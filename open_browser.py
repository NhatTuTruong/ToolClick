"""
Mở cửa sổ trình duyệt theo .env (profile, proxy) — giải CAPTCHA / cookie trước khi chạy job.

Chạy: python open_browser.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.browser_session import open_browser_session, persist_proxy_storage
from src.captcha import wait_for_captcha_clear
from src.console_io import ensure_utf8_stdio, safe_print
from src.proxy_config import ProxyRotator, parse_proxies_env, proxy_label
from playwright.sync_api import sync_playwright


def main() -> None:
    ensure_utf8_stdio()
    profile = Path(os.getenv("USER_DATA_DIR", "browser-profile"))
    locale = os.getenv("GOOGLE_LOCALE", "vi-VN")

    warmup_all = os.getenv("PROXY_WARMUP_ALL", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    lines = parse_proxies_env(os.getenv("PROXY_LIST"))
    targets: list[tuple[str, dict[str, str] | None]] = []
    if lines:
        rot = ProxyRotator.from_lines(lines)
        if rot:
            if warmup_all:
                for raw, cfg in rot.all_entries():
                    targets.append((raw, cfg))
                safe_print(f"Warmup {len(targets)} proxy trong list.")
            else:
                raw, cfg = rot.next()
                targets.append((raw, cfg))

    safe_print(
        "Dang mo Google (headed). Dong tat ca tab/cua so Chrome cua tool de ket thuc."
    )

    if not targets:
        targets = [("", None)]

    for raw, proxy_cfg in targets:
        if raw:
            safe_print(f"Proxy: {proxy_label(raw)}")
        with sync_playwright() as p:
            session = open_browser_session(
                p,
                headless=False,
                user_data_dir=profile,
                locale=locale,
                proxy=proxy_cfg,
            )
            page = (
                session.context.pages[0]
                if session.context.pages
                else session.context.new_page()
            )
            try:
                page.goto(
                    "https://www.google.com/",
                    wait_until="commit",
                    timeout=int(os.getenv("PROXY_NAV_TIMEOUT_MS", "120000")),
                )
                wait_for_captcha_clear(page, headed=True)
                persist_proxy_storage(
                    page,
                    user_data_dir=profile,
                    proxy=proxy_cfg,
                )
            except Exception as e:
                safe_print(f"Canh bao: {e}")

            if warmup_all:
                safe_print(
                    "  Da luu cookie/profile. Chuyen proxy tiep theo..."
                    if len(targets) > 1
                    else "  Giu cua so mo de duyet; dong Chrome khi xong."
                )
                if len(targets) > 1:
                    session.close()
                    continue
            try:
                while session.context.pages:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                pass
            session.close()
            if warmup_all and raw:
                safe_print(f"  Da luu profile proxy {proxy_label(raw)}.")

    safe_print("Xong. Lan sau cung proxy se nap lai cookie/profile.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        safe_print(f"Loi: {e}", file=sys.stderr)
        sys.exit(1)
