"""Danh sách proxy — parse và xoay vòng theo từng SERP."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import unquote, urlparse


def parse_proxies_text(text: str) -> list[str]:
    """Mỗi dòng / dấu phẩy / | là một proxy."""
    out: list[str] = []
    seen: set[str] = set()
    normalized = (text or "").replace("|", "\n").replace(",", "\n")
    for line in normalized.splitlines():
        raw = line.strip()
        if not raw or raw in seen:
            continue
        seen.add(raw)
        out.append(raw)
    return out


def parse_proxies_env(value: str | None) -> list[str]:
    if not value or not str(value).strip():
        return []
    raw = str(value).strip().strip('"').strip("'")
    return parse_proxies_text(raw)


def proxy_line_to_playwright(raw: str) -> dict[str, str] | None:
    line = (raw or "").strip()
    if not line:
        return None
    if "://" not in line:
        line = "http://" + line
    try:
        u = urlparse(line)
    except Exception:
        return None
    if not u.hostname:
        return None
    scheme = (u.scheme or "http").lower()
    if scheme not in ("http", "https", "socks5", "socks4"):
        scheme = "http"
    server = f"{scheme}://{u.hostname}"
    if u.port:
        server += f":{u.port}"
    out: dict[str, str] = {"server": server}
    if u.username:
        out["username"] = unquote(u.username)
    if u.password:
        out["password"] = unquote(u.password)
    return out


def proxy_profile_dir(base_user_data: Path, proxy: dict[str, str]) -> Path:
    """Thư mục cookie/storage riêng cho từng proxy (gặp lại IP → ít CAPTCHA hơn)."""
    key = "|".join(
        [
            proxy.get("server", ""),
            proxy.get("username", ""),
        ]
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return base_user_data / "proxies" / digest


def proxy_rotate_mode() -> str:
    """serp = đổi proxy mỗi SERP; keyword = một proxy cho cả từ khóa (+ mọi vòng lặp)."""
    import os

    mode = (os.getenv("PROXY_ROTATE_MODE") or "keyword").strip().lower()
    if mode in ("keyword", "kw", "per_keyword"):
        return "keyword"
    return "serp"


def proxy_label(raw: str) -> str:
    pw = proxy_line_to_playwright(raw)
    if not pw:
        return raw[:60]
    server = pw.get("server", "")
    if pw.get("username"):
        return f"{server} (auth)"
    return server


def is_proxy_connection_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    needles = (
        "err_tunnel_connection_failed",
        "err_proxy_connection_failed",
        "err_connection_refused",
        "err_connection_reset",
        "err_connection_timed_out",
        "net::err_",
        "proxy",
        "tunnel",
    )
    return any(n in msg for n in needles)


def proxy_error_hint(raw: str) -> str:
    return (
        f"Không kết nối được proxy {proxy_label(raw)}. "
        "Kiểm tra IP/port, proxy có bật không, user:pass nếu cần, "
        "hoặc thử đổi giao thức (http vs socks5://). "
        f"Lỗi thường gặp: ERR_TUNNEL_CONNECTION_FAILED."
    )


class ProxyRotator:
    """Xoay vòng proxy — mỗi lần gọi next() = một SERP mới."""

    def __init__(self, proxy_lines: list[str]) -> None:
        parsed: list[tuple[str, dict[str, str]]] = []
        for line in proxy_lines:
            cfg = proxy_line_to_playwright(line)
            if cfg:
                parsed.append((line, cfg))
        self._entries = parsed
        self._index = 0

    @classmethod
    def from_lines(cls, lines: list[str] | None) -> ProxyRotator | None:
        if not lines:
            return None
        rot = cls(lines)
        return rot if rot._entries else None

    @property
    def enabled(self) -> bool:
        return bool(self._entries)

    @property
    def count(self) -> int:
        return len(self._entries)

    def next(self) -> tuple[str, dict[str, str]]:
        if not self._entries:
            raise RuntimeError("ProxyRotator rỗng")
        raw, cfg = self._entries[self._index % len(self._entries)]
        self._index += 1
        return raw, cfg

    def first(self) -> tuple[str, dict[str, str]]:
        """Proxy đầu list (không tăng index)."""
        if not self._entries:
            raise RuntimeError("ProxyRotator rỗng")
        return self._entries[0]

    def all_entries(self) -> list[tuple[str, dict[str, str]]]:
        return list(self._entries)
