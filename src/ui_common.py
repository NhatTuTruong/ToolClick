"""Cài đặt UI dùng chung (desktop + Streamlit): .env, từ khóa."""

from __future__ import annotations

from dotenv import dotenv_values

from .job_runner import PROJECT_ROOT, JobSettings

ENV_PATH = PROJECT_ROOT / ".env"


def load_env_defaults() -> dict[str, str]:
    if ENV_PATH.is_file():
        return {k: str(v) for k, v in dotenv_values(ENV_PATH).items() if v is not None}
    return {}


def env_bool(val: str | None, default: bool) -> bool:
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def env_int(val: str | None, default: int) -> int:
    if val is None:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


def parse_keywords(text: str) -> list[str]:
    parts: list[str] = []
    for line in text.replace(",", "\n").splitlines():
        w = line.strip()
        if w:
            parts.append(w)
    return parts


def save_env_from_settings(s: JobSettings) -> None:
    lines = [
        f"HEADLESS={'false' if s.headed else 'true'}",
        f"GOOGLE_LOCALE={s.google_locale}",
        f"SEARCH_DELAY_MS={s.search_delay_ms}",
        f"BROWSER_CHANNEL={s.browser_channel}",
        f"USE_PERSISTENT_PROFILE={'true' if s.use_persistent_profile else 'false'}",
        f"USER_DATA_DIR={s.user_data_dir}",
        f"CAPTCHA_WAIT_SEC={s.captcha_wait_sec}",
        f"ORGANIC_DWELL_MS={s.organic_dwell_ms_env}",
        f"ORGANIC_CLICK_DELAY_MS={s.organic_click_delay_ms}",
        f"ENABLE_SPONSORED_CLICK_TEST={'true' if s.enable_sponsored_click_test else 'false'}",
        f"SPONSORED_DWELL_MS={s.sponsored_dwell_ms_env}",
        f"SPONSORED_CLICK_DELAY_MS={s.sponsored_click_delay_ms}",
        f"SERP_REPEAT_COUNT={s.serp_repeat if s.serp_repeat is not None else 1}",
        f"ALLOWED_CLICK_DOMAINS={','.join(s.allowed_domains) if s.allowed_domains else ''}",
        f"SKIP_CLICK_DOMAINS={','.join(s.skip_domains) if s.skip_domains else ''}",
        (
            'PROXY_LIST="' + "|".join(s.proxy_list) + '"'
            if s.proxy_list
            else "PROXY_LIST="
        ),
        f"PROXY_ROTATE_MODE={s.proxy_rotate_mode}",
        f"PROXY_PERSIST_PROFILE={'true' if s.proxy_persist_profile else 'false'}",
        f"PROXY_WARMUP_ALL={'true' if s.proxy_warmup_all else 'false'}",
        f"LICENSE_SERVER_URL={s.license_server_url or ''}",
        f"LICENSE_KEY={s.license_key or ''}",
        f"LICENSE_API_SECRET={s.license_api_secret or ''}",
        "",
    ]
    ENV_PATH.write_text("\n".join(lines), encoding="utf-8")
