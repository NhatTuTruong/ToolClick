"""Kích hoạt / kiểm tra key bản quyền với license-server Laravel."""

from __future__ import annotations

import json
import os
import platform
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

try:
    from toolclick_paths import writable_root
except ImportError:
    def writable_root() -> Path:
        return Path(__file__).resolve().parent.parent


def machine_id() -> str:
    if platform.system() == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            )
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            if guid:
                return str(guid).strip()
        except OSError:
            pass
    cached = writable_root() / ".license_machine_id"
    if cached.is_file():
        val = cached.read_text(encoding="utf-8").strip()
        if val:
            return val
    import uuid

    val = str(uuid.uuid4())
    try:
        cached.write_text(val, encoding="utf-8")
    except OSError:
        pass
    return val


def _post(url: str, payload: dict[str, Any], secret: str = "", timeout: int = 12) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "ToolClick-License/1.0",
    }
    if secret:
        headers["X-License-Secret"] = secret
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {"ok": True}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"error": raw or str(e)}
        data.setdefault("ok", False)
        err = data.get("error") or data.get("message")
        if not err:
            err = f"HTTP {e.code}"
        elif e.code >= 500 and "UNIQUE" in (raw or "").upper():
            err = "Lỗi hạn mức ngày trên server — hãy cập nhật license-server rồi thử lại."
        data["error"] = str(err)
        return data
    except Exception as e:
        return {"ok": False, "error": f"Không kết nối license-server: {e}"}


def _base_url(url: str | None = None) -> str:
    return (url or os.getenv("LICENSE_SERVER_URL") or "http://127.0.0.1:8000").rstrip("/")


def _secret(secret: str | None = None) -> str:
    return (secret if secret is not None else os.getenv("LICENSE_API_SECRET") or "").strip()


def activate(
    key: str,
    *,
    server_url: str | None = None,
    api_secret: str | None = None,
) -> dict[str, Any]:
    return _post(
        f"{_base_url(server_url)}/api/license/activate",
        {
            "key": (key or "").strip(),
            "machine_id": machine_id(),
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
        },
        _secret(api_secret),
    )


def heartbeat(
    key: str,
    *,
    records_delta: int = 0,
    server_url: str | None = None,
    api_secret: str | None = None,
) -> dict[str, Any]:
    return _post(
        f"{_base_url(server_url)}/api/license/heartbeat",
        {
            "key": (key or "").strip(),
            "machine_id": machine_id(),
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "records_delta": int(records_delta),
        },
        _secret(api_secret),
    )


def report_run(
    key: str,
    *,
    keywords: list[str] | None = None,
    click_domains: list[str] | None = None,
    skip_domains: list[str] | None = None,
    serp_rounds: int = 1,
    ads_found: int = 0,
    clicks_ok: int = 0,
    server_url: str | None = None,
    api_secret: str | None = None,
) -> dict[str, Any]:
    """Ghi thống kê lần chạy. Lỗi bị bỏ qua — không ảnh hưởng tool / key."""
    try:
        return _post(
            f"{_base_url(server_url)}/api/license/stats",
            {
                "key": (key or "").strip(),
                "keywords": keywords or [],
                "click_domains": click_domains or [],
                "skip_domains": skip_domains or [],
                "serp_rounds": max(1, int(serp_rounds or 1)),
                "ads_found": max(0, int(ads_found or 0)),
                "clicks_ok": max(0, int(clicks_ok or 0)),
                "machine_id": machine_id(),
                "hostname": platform.node(),
            },
            _secret(api_secret),
            timeout=5,
        )
    except Exception:
        return {"ok": False, "stored": False}


def verify_for_run(
    key: str,
    *,
    records_delta: int = 1,
    server_url: str | None = None,
    api_secret: str | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    key = (key or "").strip()
    if not key:
        return False, "Chưa nhập key bản quyền.", {}
    data = heartbeat(
        key,
        records_delta=records_delta,
        server_url=server_url,
        api_secret=api_secret,
    )
    if data.get("ok"):
        left = data.get("remaining_today")
        machines = data.get("machines_active")
        max_m = data.get("max_machines")
        exp = data.get("expires_at") or "không hạn"
        msg = (
            f"Key OK · máy {machines}/{max_m} · còn {left} record hôm nay · hạn {exp}"
        )
        return True, msg, data
    return False, str(data.get("error") or "Key không hợp lệ."), data
