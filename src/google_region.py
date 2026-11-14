"""Locale / host Google — khớp trình duyệt thật hơn so với /ncr + hl=vi cứng."""

from __future__ import annotations

import os
from urllib.parse import quote_plus, urlencode

# Thị trường mua sắm lớn: (GOOGLE_LOCALE, tên Việt, IANA timezone)
# Chọn nhanh trên UI; vẫn gõ tay mã khác (vd. en-US).
MARKET_LOCALES: tuple[tuple[str, str, str], ...] = (
    ("en-US", "Hoa Kỳ", "America/New_York"),
    ("en-CA", "Canada", "America/Toronto"),
    ("es-MX", "Mexico", "America/Mexico_City"),
    ("pt-BR", "Brazil", "America/Sao_Paulo"),
    ("es-AR", "Argentina", "America/Argentina/Buenos_Aires"),
    ("es-CO", "Colombia", "America/Bogota"),
    ("es-CL", "Chile", "America/Santiago"),
    ("es-PE", "Peru", "America/Lima"),
    ("en-GB", "Anh", "Europe/London"),
    ("de-DE", "Đức", "Europe/Berlin"),
    ("fr-FR", "Pháp", "Europe/Paris"),
    ("it-IT", "Ý", "Europe/Rome"),
    ("es-ES", "Tây Ban Nha", "Europe/Madrid"),
    ("nl-NL", "Hà Lan", "Europe/Amsterdam"),
    ("pl-PL", "Ba Lan", "Europe/Warsaw"),
    ("tr-TR", "Thổ Nhĩ Kỳ", "Europe/Istanbul"),
    ("sv-SE", "Thụy Điển", "Europe/Stockholm"),
    ("no-NO", "Na Uy", "Europe/Oslo"),
    ("da-DK", "Đan Mạch", "Europe/Copenhagen"),
    ("fi-FI", "Phần Lan", "Europe/Helsinki"),
    ("pt-PT", "Bồ Đào Nha", "Europe/Lisbon"),
    ("el-GR", "Hy Lạp", "Europe/Athens"),
    ("cs-CZ", "Séc", "Europe/Prague"),
    ("hu-HU", "Hungary", "Europe/Budapest"),
    ("ro-RO", "Romania", "Europe/Bucharest"),
    ("uk-UA", "Ukraine", "Europe/Kyiv"),
    ("de-AT", "Áo", "Europe/Vienna"),
    ("de-CH", "Thụy Sĩ", "Europe/Zurich"),
    ("nl-BE", "Bỉ", "Europe/Brussels"),
    ("en-IE", "Ireland", "Europe/Dublin"),
    ("sk-SK", "Slovakia", "Europe/Bratislava"),
    ("bg-BG", "Bulgaria", "Europe/Sofia"),
    ("hr-HR", "Croatia", "Europe/Zagreb"),
    ("lt-LT", "Litva", "Europe/Vilnius"),
    ("lv-LV", "Latvia", "Europe/Riga"),
    ("et-EE", "Estonia", "Europe/Tallinn"),
    ("ja-JP", "Nhật Bản", "Asia/Tokyo"),
    ("ko-KR", "Hàn Quốc", "Asia/Seoul"),
    ("zh-TW", "Đài Loan", "Asia/Taipei"),
    ("zh-HK", "Hồng Kông", "Asia/Hong_Kong"),
    ("en-AU", "Úc", "Australia/Sydney"),
    ("en-NZ", "New Zealand", "Pacific/Auckland"),
    ("en-SG", "Singapore", "Asia/Singapore"),
    ("hi-IN", "Ấn Độ", "Asia/Kolkata"),
    ("id-ID", "Indonesia", "Asia/Jakarta"),
    ("th-TH", "Thái Lan", "Asia/Bangkok"),
    ("vi-VN", "Việt Nam", "Asia/Ho_Chi_Minh"),
    ("ms-MY", "Malaysia", "Asia/Kuala_Lumpur"),
    ("en-PH", "Philippines", "Asia/Manila"),
    ("bn-BD", "Bangladesh", "Asia/Dhaka"),
    ("ur-PK", "Pakistan", "Asia/Karachi"),
    ("ar-SA", "Ả Rập Xê Út", "Asia/Riyadh"),
    ("ar-AE", "UAE", "Asia/Dubai"),
    ("he-IL", "Israel", "Asia/Jerusalem"),
    ("ar-EG", "Ai Cập", "Africa/Cairo"),
    ("ar-QA", "Qatar", "Asia/Qatar"),
    ("ar-KW", "Kuwait", "Asia/Kuwait"),
    ("ar-MA", "Maroc", "Africa/Casablanca"),
    ("en-NG", "Nigeria", "Africa/Lagos"),
    ("en-ZA", "Nam Phi", "Africa/Johannesburg"),
    ("en-KE", "Kenya", "Africa/Nairobi"),
    ("es-EC", "Ecuador", "America/Guayaquil"),
)

_TIMEZONE_BY_GL: dict[str, str] = {}
for _code, _name, _tz in MARKET_LOCALES:
    _gl = _code.split("-")[-1].upper()
    _TIMEZONE_BY_GL.setdefault(_gl, _tz)


def locale_choice_labels() -> list[str]:
    return [f"{code}  ({name})" for code, name, _tz in MARKET_LOCALES]


def locale_label_for(code: str | None) -> str:
    raw = (code or "").replace("_", "-").strip()
    if not raw:
        return locale_label_for("vi-VN")
    for c, name, _tz in MARKET_LOCALES:
        if c.lower() == raw.lower():
            return f"{c}  ({name})"
    return raw


def parse_locale_choice(value: str | None) -> str:
    s = (value or "").strip()
    if not s:
        return "vi-VN"
    token = s.replace("(", " ").replace("—", " ").replace("–", " ").split()[0]
    token = token.strip(" ,;")
    if not token:
        return "vi-VN"
    return token.replace("_", "-")


def locale_hl_gl(locale: str | None = None) -> tuple[str, str]:
    loc = (locale or os.getenv("GOOGLE_LOCALE") or "vi-VN").replace("_", "-").strip()
    parts = [p for p in loc.split("-") if p]
    hl = parts[0].lower() if parts else "vi"
    gl = parts[1].upper() if len(parts) > 1 else "VN"
    env_hl = (os.getenv("GOOGLE_HL") or "").strip()
    env_gl = (os.getenv("GOOGLE_GL") or "").strip()
    if env_hl:
        hl = env_hl
    if env_gl:
        gl = env_gl.upper()
    return hl, gl


def accept_language_header(locale: str | None = None) -> str:
    override = (os.getenv("BROWSER_ACCEPT_LANGUAGE") or "").strip()
    if override:
        return override
    hl, gl = locale_hl_gl(locale)
    return f"{hl}-{gl},{hl};q=0.9,en-US;q=0.8,en;q=0.7"


def timezone_id(locale: str | None = None) -> str:
    override = (os.getenv("GOOGLE_TIMEZONE") or "").strip()
    if override:
        return override
    _hl, gl = locale_hl_gl(locale)
    return _TIMEZONE_BY_GL.get(gl, "UTC")


def google_host(locale: str | None = None) -> str:
    override = (os.getenv("GOOGLE_HOST") or "").strip()
    if override:
        return override.removeprefix("https://").removeprefix("http://").strip("/")
    _hl, gl = locale_hl_gl(locale)
    if gl == "VN":
        return "www.google.com.vn"
    return "www.google.com"


def google_home_url(locale: str | None = None) -> str:
    hl, gl = locale_hl_gl(locale)
    host = google_host(locale)
    return f"https://{host}/?hl={hl}&gl={gl}"


def google_search_url(keyword: str, locale: str | None = None) -> str:
    hl, gl = locale_hl_gl(locale)
    host = google_host(locale)
    q = keyword.strip()
    qs = urlencode({"q": q, "hl": hl, "gl": gl}, quote_via=quote_plus)
    return f"https://{host}/search?{qs}"
