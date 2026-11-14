"""
Quy tắc duy nhất phân biệt quảng cáo (Sponsored) vs kết quả organic.

Mọi chỗ extract hoặc click organic PHẢI dùng:
  - JS: anchorIsSponsoredAd / hrefIsSponsoredAdUrl (từ JS_SERP_AD_HELPERS_IIFE)
  - Python: href_is_sponsored_ad_url / assert_href_safe_for_organic_click

Không copy điều kiện lọc sang file khác.
"""

from __future__ import annotations

import os
from urllib.parse import parse_qs, urlparse

SPONSORED_TEXT_LABELS: tuple[str, ...] = (
    "sponsored",
    "quảng cáo",
    "quang cao",
    "广告",
    "anuncio",
    "gesponsert",
    "publicité",
    "annuncio",
)

SPONSORED_BLOCK_CSS_SELECTORS: tuple[str, ...] = (
    "[data-text-ad]",
    "[data-text-ad='1']",
    "div.uEierd",
    "div.v5yQqb",
    ".commercial-unit-desktop-top",
    ".commercial-unit-desktop-rhs",
)


class SponsoredAdClickBlockedError(RuntimeError):
    """Chặn click vì URL/anchor được xác định là quảng cáo."""


def _labels_js_array() -> str:
    return str(list(SPONSORED_TEXT_LABELS)).replace("'", '"')


def _block_selectors_js() -> str:
    return ", ".join(SPONSORED_BLOCK_CSS_SELECTORS)


# Biểu thức IIFE — gán: const helpers = <IIFE>;
JS_SERP_AD_HELPERS_IIFE = f"""(() => {{
  const SPONSORED_TEXT_LABELS = {_labels_js_array()};
  const SPONSORED_BLOCK_SELECTOR = "{_block_selectors_js()}";

  function hrefIsSponsoredAdUrl(href) {{
    if (!href) return true;
    const h = String(href).toLowerCase();
    if (h.includes('/aclk')) return true;
    if (h.includes('googleadservices.com')) return true;
    if (h.includes('doubleclick.net')) return true;
    if (h.includes('adurl=')) return true;
    if (h.includes('google.com/goto')) return true;
    if (h.includes('google.com/url') && h.includes('adurl=')) return true;
    return false;
  }}

  function elementIsInsideSponsoredBlock(el) {{
    if (!el || !el.closest) return true;
    if (el.closest(SPONSORED_BLOCK_SELECTOR)) return true;
    return false;
  }}

  function elementHasSponsoredTextLabel(el) {{
    const norm = (s) => (s || '').replace(/\\s+/g, ' ').trim().toLowerCase();
    let node = el;
    for (let i = 0; i < 8 && node; i++) {{
      const t = norm(node.innerText || node.textContent || '');
      if (t && t.length <= 48) {{
        for (const lbl of SPONSORED_TEXT_LABELS) {{
          if (t === lbl || t.startsWith(lbl + ' ') || t.endsWith(' ' + lbl)) return true;
        }}
      }}
      node = node.parentElement;
    }}
    return false;
  }}

  function anchorIsSponsoredAd(anchor) {{
    if (!anchor || anchor.tagName !== 'A') return true;
    if (hrefIsSponsoredAdUrl(anchor.href)) return true;
    if (elementIsInsideSponsoredBlock(anchor)) return true;
    if (elementHasSponsoredTextLabel(anchor)) return true;
    return false;
  }}

  return {{ hrefIsSponsoredAdUrl, anchorIsSponsoredAd, elementIsInsideSponsoredBlock }};
}})()"""


def href_is_sponsored_ad_url(href: str) -> bool:
    if not href:
        return True
    h = href.lower()
    return (
        "/aclk" in h
        or "googleadservices.com" in h
        or "doubleclick.net" in h
        or "adurl=" in h
        or "google.com/goto" in h
    )


def assert_href_safe_for_organic_click(href: str, *, context: str = "") -> None:
    if href_is_sponsored_ad_url(href):
        msg = f"Chặn click: URL là quảng cáo ({href[:120]})"
        if context:
            msg = f"{context}: {msg}"
        raise SponsoredAdClickBlockedError(msg)


def env_flag_enabled(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def sponsored_click_test_enabled() -> bool:
    """
    Bật click quảng cáo Sponsored (chỉ môi trường test).
    Mặc định false — cần ENABLE_SPONSORED_CLICK_TEST=true trong .env.
    """
    return env_flag_enabled("ENABLE_SPONSORED_CLICK_TEST", False)


def normalize_href_for_compare(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    try:
        p = urlparse(href)
        if "google." in p.netloc and p.path == "/url":
            q = parse_qs(p.query)
            if q.get("q"):
                return q["q"][0].split("#")[0].rstrip("/")
    except Exception:
        pass
    return href.split("#")[0].rstrip("/")
