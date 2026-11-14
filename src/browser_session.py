"""Mở trình duyệt Playwright: profile persistent hoặc session + storage_state."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Playwright

from .console_io import safe_print
from .google_region import accept_language_header, timezone_id
from .proxy_config import proxy_profile_dir

_BROWSER_INSTALL_HINT = (
    "Không tìm thấy Google Chrome hoặc Microsoft Edge.\n"
    "Bản ToolClick.exe dùng Chrome/Edge đã cài trên máy — không kèm Chromium Playwright.\n"
    "Cài Chrome: https://www.google.com/chrome/ rồi chạy lại.\n"
    "Chạy từ source: python -m playwright install chromium (chỉ khi BROWSER_CHANNEL=chromium)."
)

_STEALTH_INIT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
"""


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _realistic() -> bool:
    return _env_bool("REALISTIC_BROWSER", True)


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _windows_browser_exes(kind: str) -> list[Path]:
    local = os.environ.get("LOCALAPPDATA", "")
    pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    pf86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    if kind == "chrome":
        cands = [
            Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(pf86) / "Google" / "Chrome" / "Application" / "chrome.exe",
            Path(local) / "Google" / "Chrome" / "Application" / "chrome.exe",
        ]
    else:
        cands = [
            Path(pf) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(pf86) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
            Path(local) / "Microsoft" / "Edge" / "Application" / "msedge.exe",
        ]
    return [p for p in cands if p.is_file()]


def _launch_tries() -> list[dict]:
    """Ưu tiên chrome.exe / msedge.exe trên đĩa — bản .exe không có Chromium Playwright."""
    mode = (os.getenv("BROWSER_CHANNEL") or "chrome").strip().lower()
    frozen = _is_frozen()
    if mode == "chromium" and frozen:
        mode = "chrome"

    kinds: list[str]
    if mode == "msedge":
        kinds = ["msedge", "chrome"]
    elif mode == "chromium":
        kinds = ["chromium", "chrome", "msedge"]
    elif mode == "chrome":
        kinds = ["chrome", "msedge"]
    else:
        kinds = ["chrome", "msedge"]
        if not frozen:
            kinds.append("chromium")

    tries: list[dict] = []
    seen: set[str] = set()

    def _add(kw: dict) -> None:
        key = str(sorted(kw.items()))
        if key in seen:
            return
        seen.add(key)
        tries.append(kw)

    for kind in kinds:
        if kind == "chromium":
            if not frozen:
                _add({})
            continue
        if sys.platform == "win32":
            for exe in _windows_browser_exes(kind):
                _add({"executable_path": str(exe)})
        _add({"channel": kind})
    return tries


def _proxy_launch_args() -> list[str]:
    return [
        "--disable-quic",
        "--disable-http2",
        "--dns-prefetch-disable",
    ]


def _chrome_args(*, use_proxy: bool, locale: str, headless: bool) -> list[str]:
    args = [
        "--disable-blink-features=AutomationControlled",
        f"--lang={locale}",
        "--disable-infobars",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if not headless and _realistic():
        args.append("--start-maximized")
    if use_proxy:
        args.extend(_proxy_launch_args())
    return args


def _context_options(
    *,
    locale: str,
    proxy: dict | None = None,
    headless: bool = False,
) -> dict:
    opts: dict = {
        "locale": locale,
        "timezone_id": timezone_id(locale),
        "color_scheme": "light",
        "extra_http_headers": {
            "Accept-Language": accept_language_header(locale),
        },
    }
    ua = (os.getenv("BROWSER_USER_AGENT") or "").strip()
    if ua:
        opts["user_agent"] = ua
    # Không ghi đè UA Chrome thật khi dùng channel=chrome (gần trình duyệt thường hơn).
    if headless or not _realistic():
        w = int(os.getenv("BROWSER_VIEWPORT_W", "1920"))
        h = int(os.getenv("BROWSER_VIEWPORT_H", "1080"))
        opts["viewport"] = {"width": w, "height": h}
        opts["screen"] = {"width": w, "height": h}
    else:
        # None = cửa sổ thật (start-maximized), không ép 1366×900.
        opts["viewport"] = None
    if proxy:
        opts["proxy"] = proxy
        opts["ignore_https_errors"] = True
    return opts


def _apply_init_scripts(context: BrowserContext) -> None:
    if not _realistic():
        return
    try:
        context.add_init_script(_STEALTH_INIT)
    except Exception:
        pass


@dataclass
class BrowserSession:
    context: BrowserContext
    browser: Browser | None
    storage_path: Path
    mode: str

    def save_cookies(self) -> None:
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.context.storage_state(path=str(self.storage_path))
        except Exception:
            pass

    def close(self) -> None:
        self.save_cookies()
        try:
            self.context.close()
        except Exception:
            pass
        if self.browser is not None:
            try:
                self.browser.close()
            except Exception:
                pass


def persist_proxy_storage(
    page,
    *,
    user_data_dir: Path,
    proxy: dict[str, str] | None,
) -> None:
    """Ghi cookie ngay sau CAPTCHA / SERP — lần sau cùng proxy đỡ CAPTCHA hơn."""
    if not proxy:
        return
    _, storage_path = resolve_profile_paths(user_data_dir, proxy)
    try:
        page.context.storage_state(path=str(storage_path))
    except Exception:
        pass


def resolve_profile_paths(
    user_data_dir: Path, proxy: dict | None
) -> tuple[Path, Path]:
    if proxy:
        profile = proxy_profile_dir(user_data_dir, proxy)
        profile.mkdir(parents=True, exist_ok=True)
        return profile, profile / "storage_state.json"
    return user_data_dir, user_data_dir / "storage_state.json"


def profile_has_saved_state(profile_dir: Path, storage_path: Path) -> bool:
    if storage_path.is_file():
        return True
    return (profile_dir / "Default").is_dir()


def _launch_browser(
    p: Playwright,
    *,
    headless: bool,
    use_proxy: bool = False,
    locale: str = "vi-VN",
) -> Browser:
    last_err: Exception | None = None
    args = _chrome_args(use_proxy=use_proxy, locale=locale, headless=headless)
    for extra in _launch_tries():
        try:
            return p.chromium.launch(
                headless=headless,
                args=args,
                ignore_default_args=["--enable-automation"],
                **extra,
            )
        except Exception as e:
            last_err = e
            if "Executable doesn't exist" not in str(e):
                raise
    raise RuntimeError(_BROWSER_INSTALL_HINT) from last_err


def _try_persistent(
    p: Playwright,
    *,
    headless: bool,
    user_data_dir: Path,
    locale: str,
    proxy: dict | None = None,
) -> BrowserContext | None:
    user_data_dir.mkdir(parents=True, exist_ok=True)
    base_kw: dict = {
        "user_data_dir": str(user_data_dir.resolve()),
        "headless": headless,
        **_context_options(locale=locale, proxy=proxy, headless=headless),
        "args": _chrome_args(use_proxy=proxy is not None, locale=locale, headless=headless),
        "ignore_default_args": ["--enable-automation"],
    }
    for extra in _launch_tries():
        try:
            ctx = p.chromium.launch_persistent_context(**base_kw, **extra)
            _apply_init_scripts(ctx)
            return ctx
        except Exception as e:
            err = str(e)
            if "Executable doesn't exist" in err:
                continue
            if "TargetClosedError" in type(e).__name__ or "has been closed" in err:
                continue
            raise
    return None


def _open_ephemeral(
    p: Playwright,
    *,
    headless: bool,
    user_data_dir: Path,
    locale: str,
    proxy: dict | None = None,
) -> BrowserSession:
    _profile_dir, storage_path = resolve_profile_paths(user_data_dir, proxy)
    browser = _launch_browser(
        p, headless=headless, use_proxy=proxy is not None, locale=locale
    )
    ctx_kw = _context_options(locale=locale, proxy=proxy, headless=headless)
    if storage_path.is_file():
        ctx_kw["storage_state"] = str(storage_path)
    context = browser.new_context(**ctx_kw)
    _apply_init_scripts(context)
    return BrowserSession(
        context=context,
        browser=browser,
        storage_path=storage_path,
        mode="ephemeral",
    )


def open_browser_session(
    p: Playwright,
    *,
    headless: bool,
    user_data_dir: Path,
    locale: str,
    proxy: dict | None = None,
) -> BrowserSession:
    user_data_dir.mkdir(parents=True, exist_ok=True)
    profile_dir, storage_path = resolve_profile_paths(user_data_dir, proxy)

    persist_default = _realistic()
    use_persistent = _env_bool("USE_PERSISTENT_PROFILE", persist_default) and proxy is None

    if proxy and _env_bool("PROXY_PERSIST_PROFILE", True):
        if profile_has_saved_state(profile_dir, storage_path):
            safe_print(
                f"[proxy] Tai lai profile/cookie da luu ({profile_dir.name}) — "
                f"cung proxy se it CAPTCHA hon."
            )
        ctx = _try_persistent(
            p,
            headless=headless,
            user_data_dir=profile_dir,
            locale=locale,
            proxy=proxy,
        )
        if ctx is not None:
            return BrowserSession(
                context=ctx,
                browser=None,
                storage_path=storage_path,
                mode="persistent",
            )
        safe_print(
            "[proxy] Chrome profile rieng that bai — fallback storage_state.json.",
            file=sys.stderr,
        )

    if use_persistent:
        ctx = _try_persistent(
            p,
            headless=headless,
            user_data_dir=user_data_dir,
            locale=locale,
            proxy=proxy,
        )
        if ctx is not None:
            safe_print("Browser: Chrome + profile co dinh (gan trinh duyet that).")
            return BrowserSession(
                context=ctx,
                browser=None,
                storage_path=storage_path,
                mode="persistent",
            )
        safe_print(
            "Khong mo duoc browser-profile — chuyen sang session + storage_state.json.",
            file=sys.stderr,
        )

    session = _open_ephemeral(
        p,
        headless=headless,
        user_data_dir=user_data_dir,
        locale=locale,
        proxy=proxy,
    )
    if session.mode == "ephemeral":
        if proxy:
            user = proxy.get("username")
            auth = " (auth)" if user else ""
            if storage_path.is_file():
                safe_print(f"[proxy] Nap storage_state + proxy {proxy.get('server', '')}{auth}")
            else:
                safe_print(f"Browser: session + proxy {proxy.get('server', '')}{auth}")
        else:
            safe_print("Browser: session + storage_state.json")
    return session
