"""
Click quảng cáo trên CÙNG một SERP — mỗi ad mở tab mới, tab SERP giữ nguyên.
max_clicks=0 → click hết ads trên SERP hiện tại.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, asdict
from typing import Any

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .serp_ad_guard import sponsored_click_test_enabled
from .serp_dom_scripts import (
    script_find_sponsored_anchor_element,
    script_sponsored_target_visible,
)
from .serp_navigation import (
    count_sponsored_on_serp,
    scroll_serp_for_ads,
    wait_for_serp_ads_ready,
)
from .domain_filter import filter_sponsored_for_click
from .sponsored_parser import SponsoredResult


@dataclass
class SponsoredClickStat:
    keyword: str
    rank: int
    title: str
    serp_href: str
    final_url: str
    status: str
    error: str
    dwell_ms: int
    serp_round: int = 1

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    return int(v.strip())


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _new_tab_modifiers() -> list[str]:
    return ["Meta"] if sys.platform == "darwin" else ["Control"]


def _target_payload(item: SponsoredResult) -> dict:
    return {
        "rank": item.rank,
        "href": item.destination_url,
        "title": item.title,
    }


def _close_extra_tabs(serp_page: Page) -> None:
    for tab in list(serp_page.context.pages):
        if tab is serp_page:
            continue
        try:
            tab.close()
        except Exception:
            pass


def _find_sponsored_anchor(page: Page, payload: dict) -> Any:
    handle = page.evaluate_handle(script_find_sponsored_anchor_element(), payload)
    if handle is None:
        return None
    el = handle.as_element()
    if el is None:
        try:
            handle.dispose()
        except Exception:
            pass
    return el


def _click_sponsored_new_tab(
    serp_page: Page,
    payload: dict,
    *,
    timeout_ms: int = 25000,
) -> tuple[dict[str, Any], Page | None]:
    """
    Ctrl/Meta+click (hoặc middle-click) — SERP không đổi tab.
    """
    anchor = _find_sponsored_anchor(serp_page, payload)
    if anchor is None:
        return {
            "clicked": False,
            "reason": "not_found",
            "listed": count_sponsored_on_serp(serp_page),
        }, None

    picked_href = anchor.get_attribute("href") or payload.get("href") or ""
    title = payload.get("title") or ""

    _close_extra_tabs(serp_page)
    ad_page: Page | None = None
    serp_url_before = serp_page.url

    for button, modifiers in (
        ("left", _new_tab_modifiers()),
        ("middle", []),
    ):
        try:
            with serp_page.context.expect_page(timeout=timeout_ms) as pinfo:
                if modifiers:
                    anchor.click(modifiers=modifiers)
                else:
                    anchor.click(button=button)
            ad_page = pinfo.value
            break
        except PlaywrightTimeout:
            continue
        except Exception:
            continue

    try:
        anchor.dispose()
    except Exception:
        pass

    if ad_page is None:
        if serp_page.url != serp_url_before and "google.com/search" not in (
            serp_page.url or ""
        ):
            return {
                "clicked": False,
                "reason": "same_tab_nav",
                "picked_href": picked_href,
                "title": title,
            }, None
        return {
            "clicked": False,
            "reason": "no_new_tab",
            "listed": count_sponsored_on_serp(serp_page),
            "picked_href": picked_href,
            "title": title,
        }, None

    return {
        "clicked": True,
        "reason": "",
        "picked_href": picked_href,
        "title": title,
    }, ad_page


def resolve_sponsored_click_count(max_clicks: int, available: int) -> int:
    if available <= 0:
        return 0
    if max_clicks <= 0:
        return available
    return min(max_clicks, available)


def click_sponsored_on_current_serp(
    page: Page,
    *,
    keyword: str,
    sponsored: list[SponsoredResult],
    max_clicks: int,
    dwell_ms: int | None = None,
    serp_round: int = 1,
    allowed_domains: list[str] | None = None,
    skip_domains: list[str] | None = None,
) -> list[SponsoredClickStat]:
    """
    Click lần lượt trên SERP đang mở — mỗi quảng cáo mở tab mới, không go_back/reload SERP.
    """
    if not sponsored_click_test_enabled():
        raise RuntimeError(
            "Click quảng cáo bị tắt. Đặt ENABLE_SPONSORED_CLICK_TEST=true trong .env."
        )

    allowed = allowed_domains or []
    skip = skip_domains or []
    pool = filter_sponsored_for_click(sponsored, allowed, skip)
    available = len(pool)
    if available == 0:
        if (allowed or skip) and sponsored:
            parts = []
            if allowed:
                parts.append(f"khớp domain {', '.join(allowed)}")
            if skip:
                parts.append(f"không thuộc domain bỏ qua {', '.join(skip)}")
            print(
                f"  [sponsored] Không có quảng cáo {' và '.join(parts)} "
                f"(tìm thấy {len(sponsored)} trên SERP)."
            )
        return []

    clicks_to_do = resolve_sponsored_click_count(max_clicks, available)
    if clicks_to_do <= 0:
        return []

    prefix = f"[serp-round {serp_round}] " if serp_round > 1 else ""
    domain_note = ""
    if allowed:
        domain_note += f" (lọc domain: {', '.join(allowed)})"
    if skip:
        domain_note += f" (bỏ qua: {', '.join(skip)})"
    open_new = _env_bool("SPONSORED_OPEN_NEW_TAB", True)
    mode_note = " (tab mới, SERP giữ nguyên)" if open_new else ""
    print(
        f"  {prefix}[sponsored] Click {clicks_to_do}/{available} quảng cáo "
        f"trên SERP{domain_note}{mode_note}."
    )
    skipped_n = len(sponsored) - len(pool)
    if skipped_n > 0 and (allowed or skip):
        reasons = []
        if allowed:
            reasons.append("không thuộc domain cho phép")
        if skip:
            reasons.append("nằm trong domain không click")
        print(
            f"  {prefix}[sponsored] Bỏ qua {skipped_n} quảng cáo "
            f"({'; '.join(reasons)})."
        )

    dwell = dwell_ms if dwell_ms is not None else _env_int("SPONSORED_DWELL_MS", 1000)
    pause = _env_int("SPONSORED_CLICK_DELAY_MS", 300) / 1000.0
    tab_timeout = _env_int("SPONSORED_NEW_TAB_TIMEOUT_MS", 25000)
    stats: list[SponsoredClickStat] = []
    serp_url = page.url
    wait_for_serp_ads_ready(page, min_count=1, timeout_sec=8.0)

    targets = pool[:clicks_to_do]
    for idx, item in enumerate(targets):
        print(f"  {prefix}[sponsored #{item.rank}] {item.title[:70]}...")
        status = "ok"
        err = ""
        final_url = ""
        picked_href = item.destination_url
        result: dict[str, Any] = {}

        try:
            if "google.com/search" not in (page.url or ""):
                raise RuntimeError(
                    "Tab SERP không còn ở trang search — không reload giữa các click."
                )

            payload = _target_payload(item)
            if not page.evaluate(script_sponsored_target_visible(), payload):
                scroll_serp_for_ads(page)

            if open_new:
                result, ad_page = _click_sponsored_new_tab(
                    page, payload, timeout_ms=tab_timeout
                )
            else:
                from .serp_dom_scripts import script_click_sponsored_target_for_test

                result = page.evaluate(script_click_sponsored_target_for_test(), payload)
                ad_page = None

            if not result.get("clicked"):
                reason = result.get("reason", "?")
                n = result.get("listed", count_sponsored_on_serp(page))
                raise RuntimeError(
                    f"Không mở được quảng cáo ({reason}, trên SERP: {n}): "
                    f"{item.title[:60]}"
                )

            picked_href = result.get("picked_href") or picked_href
            if ad_page is not None:
                try:
                    ad_page.wait_for_load_state("domcontentloaded", timeout=12000)
                except PlaywrightTimeout:
                    pass
                time.sleep(dwell / 1000.0)
                final_url = ad_page.url
                try:
                    ad_page.close()
                except Exception:
                    pass
                try:
                    page.bring_to_front()
                except Exception:
                    pass
            else:
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=12000)
                except PlaywrightTimeout:
                    pass
                time.sleep(dwell / 1000.0)
                final_url = page.url

            if "google.com/search" not in (page.url or ""):
                raise RuntimeError("Tab SERP bị chuyển trang sau click — bật SPONSORED_OPEN_NEW_TAB=true.")

        except PlaywrightTimeout as e:
            status = "timeout"
            err = str(e)[:200]
            final_url = page.url
            _close_extra_tabs(page)
        except Exception as e:
            status = "error"
            err = str(e)[:300]
            final_url = page.url
            print(f"    ⚠ {err}")
            _close_extra_tabs(page)

        stats.append(
            SponsoredClickStat(
                keyword=keyword or item.keyword,
                rank=item.rank,
                title=(result.get("title") or item.title) if status == "ok" else item.title,
                serp_href=picked_href,
                final_url=final_url,
                status=status,
                error=err,
                dwell_ms=dwell,
                serp_round=serp_round,
            )
        )

        if status == "ok" and idx < len(targets) - 1:
            _close_extra_tabs(page)
            if page.url != serp_url and "google.com/search" in (page.url or ""):
                serp_url = page.url
            time.sleep(pause)

    _close_extra_tabs(page)
    return stats


click_sponsored_results_for_test = click_sponsored_on_current_serp
