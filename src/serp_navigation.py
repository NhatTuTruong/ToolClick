"""Quay lại SERP sau khi click (tab mới, redirect, go_back / goto lỗi)."""

from __future__ import annotations

import time
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .google_region import google_search_url
from .serp_dom_scripts import script_list_sponsored_anchors, script_scroll_serp_for_ads


def stable_search_url(keyword: str, fallback_url: str = "") -> str:
    """URL SERP ngắn, ổn định — tránh goto URL tracking dài gây ERR_ABORTED."""
    q = keyword.strip()
    if not q and fallback_url:
        try:
            qs = parse_qs(urlparse(fallback_url).query)
            if qs.get("q"):
                q = qs["q"][0]
        except Exception:
            pass
    if not q:
        return fallback_url or "https://www.google.com/"
    return google_search_url(q)


def count_sponsored_on_serp(page: Page) -> int:
    try:
        rows: list = page.evaluate(script_list_sponsored_anchors())
        return len(rows)
    except Exception:
        return 0


def scroll_serp_for_ads(page: Page) -> None:
    try:
        page.evaluate(script_scroll_serp_for_ads())
    except Exception:
        pass


def wait_for_serp_ads_ready(
    page: Page,
    *,
    min_count: int = 1,
    timeout_sec: float = 22.0,
) -> int:
    """Chờ khối quảng cáo render sau go_back / bfcache (tránh click khi listed=0)."""
    if min_count <= 0:
        return count_sponsored_on_serp(page)

    if "google.com/search" in (page.url or ""):
        last = count_sponsored_on_serp(page)
        if last >= min_count:
            return last

    deadline = time.time() + timeout_sec
    last = 0
    while time.time() < deadline:
        if "google.com/search" not in (page.url or ""):
            time.sleep(0.15)
            continue
        last = count_sponsored_on_serp(page)
        if last >= min_count:
            return last
        try:
            page.wait_for_load_state("domcontentloaded", timeout=2000)
        except PlaywrightTimeout:
            pass
        try:
            page.wait_for_selector(
                "#tads, #tadsb, #bottomads, [data-text-ad], .uEierd",
                timeout=1200,
            )
        except PlaywrightTimeout:
            pass
        last = count_sponsored_on_serp(page)
        if last >= min_count:
            return last
        time.sleep(0.2)
    return last


def reload_serp_for_ads(page: Page, *, keyword: str, fallback_serp_url: str) -> None:
    target = stable_search_url(keyword, fallback_serp_url)
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            if attempt:
                time.sleep(1.5 * attempt)
            page.goto(target, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_selector(
                    "#tads, #tadsb, [data-text-ad], .uEierd, #rso",
                    timeout=22000,
                )
            except PlaywrightTimeout:
                pass
            time.sleep(1.0)
            return
        except Exception as e:
            last_err = e
            if "google.com/search" in (page.url or ""):
                time.sleep(1.2)
                return
    if last_err and "google.com/search" not in (page.url or ""):
        raise last_err


def restore_serp_after_click(
    page: Page,
    serp_url: str,
    *,
    keyword: str = "",
    prefer_exact_url: bool = False,
    ads_ready_timeout_sec: float = 14.0,
) -> None:
    target = serp_url if prefer_exact_url and serp_url else stable_search_url(keyword, serp_url)
    context = page.context
    for extra in list(context.pages):
        if extra is page:
            continue
        try:
            extra.close()
        except Exception:
            pass

    time.sleep(0.2)

    if _is_serp_url(page.url, target):
        scroll_serp_for_ads(page)
        wait_for_serp_ads_ready(
            page, min_count=1, timeout_sec=ads_ready_timeout_sec
        )
        return

    try:
        page.go_back(wait_until="domcontentloaded", timeout=10000)
        if _is_serp_url(page.url, target):
            scroll_serp_for_ads(page)
            wait_for_serp_ads_ready(
                page, min_count=1, timeout_sec=ads_ready_timeout_sec
            )
            return
    except Exception:
        pass

    try:
        page.goto(target, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        pass
    scroll_serp_for_ads(page)
    wait_for_serp_ads_ready(
        page,
        min_count=1,
        timeout_sec=max(ads_ready_timeout_sec, 10.0),
    )


def _is_serp_url(current: str, serp_url: str) -> bool:
    if not current:
        return False
    if "google.com/search" not in current:
        return False
    try:
        cq = parse_qs(urlparse(current).query).get("q", [""])[0]
        sq = parse_qs(urlparse(serp_url).query).get("q", [""])[0]
        if cq and sq and cq == sq:
            return True
    except Exception:
        pass
    return "google.com/search" in serp_url
