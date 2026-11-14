"""Phát hiện CAPTCHA Google và chờ người dùng giải thủ công (headed)."""

from __future__ import annotations

import os
import time


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    return int(v.strip())


def is_google_captcha(page) -> bool:
    url = (page.url or "").lower()
    if "/sorry/" in url or "google.com/sorry" in url:
        return True

    try:
        return bool(
            page.evaluate(
                """() => {
                  if (document.querySelector('form#captcha-form, form[action*="sorry"]')) return true;
                  if (document.querySelector('iframe[src*="recaptcha"], iframe[title*="reCAPTCHA"]')) return true;
                  const t = (document.body && document.body.innerText) || '';
                  const low = t.toLowerCase();
                  if (low.includes('unusual traffic') || low.includes('lưu lượng bất thường')) return true;
                  if (low.includes('not a robot') || low.includes('không phải người máy')) return true;
                  if (low.includes('xác minh') && low.includes('robot')) return true;
                  return false;
                }"""
            )
        )
    except Exception:
        return False


def page_looks_like_serp(page) -> bool:
    try:
        return bool(
            page.evaluate(
                """() => {
                  if (document.querySelector('#search, div#rso, div[data-async-context]')) return true;
                  const q = document.querySelector('textarea[name="q"], input[name="q"]');
                  return !!(q && location.href.includes('/search'));
                }"""
            )
        )
    except Exception:
        return False


def wait_for_captcha_clear(page, *, headed: bool) -> None:
    if not is_google_captcha(page):
        return

    timeout = _env_int("CAPTCHA_WAIT_SEC", 300)
    if not headed:
        raise RuntimeError(
            "Google đang hiện CAPTCHA. Không thể giải tự động.\n"
            "Chạy: python main.py -k \"từ khóa\" --headed\n"
            "Giải CAPTCHA trong cửa sổ trình duyệt; profile lưu tại USER_DATA_DIR (mặc định browser-profile/)."
        )

    print(
        "\n*** CAPTCHA ***\n"
        "Giải CAPTCHA trong cửa sổ trình duyệt (tick 'Tôi không phải người máy' / puzzle).\n"
        "Moi IP proxy moi thuong bi CAPTCHA — cookie luu trong browser-profile/proxies/.\n"
        "Goi y: PROXY_ROTATE_MODE=keyword hoac chi 1 proxy trong list.\n"
        f"Tool sẽ chờ tối đa {timeout}s...\n"
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        page.wait_for_timeout(1000)
        if not is_google_captcha(page) and (page_looks_like_serp(page) or "google.com" in page.url):
            print("CAPTCHA đã qua (hoặc đã về trang Google). Tiếp tục...\n")
            return
    raise RuntimeError(f"Hết {timeout}s chờ CAPTCHA. Thử lại với --headed và profile browser-profile/.")
