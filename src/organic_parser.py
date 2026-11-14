"""Trích xuất kết quả organic — lọc quảng cáo qua serp_ad_guard + so sánh URL sponsored."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict, replace
from typing import Any

from .serp_ad_guard import href_is_sponsored_ad_url, normalize_href_for_compare
from .serp_dom_scripts import script_extract_organic_anchors
from .sponsored_parser import SponsoredResult


@dataclass
class OrganicResult:
    keyword: str
    rank: int
    title: str
    href: str
    display_url: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OrganicClickStat:
    keyword: str
    rank: int
    title: str
    serp_href: str
    final_url: str
    status: str
    error: str
    dwell_ms: int

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_organic_from_page(page, keyword: str) -> list[OrganicResult]:
    raw: list[dict] = page.evaluate(script_extract_organic_anchors())
    results: list[OrganicResult] = []
    for i, item in enumerate(raw, start=1):
        href = item.get("href") or ""
        if href_is_sponsored_ad_url(href):
            continue
        results.append(
            OrganicResult(
                keyword=keyword,
                rank=i,
                title=_normalize(item.get("title", "")),
                href=href,
                display_url=_normalize(item.get("display_url", "")),
            )
        )
    return results


def finalize_organic_list(
    organic: list[OrganicResult],
    sponsored: list[SponsoredResult],
) -> list[OrganicResult]:
    """
    Lớp lọc Python (sau DOM): loại organic trùng URL quảng cáo đã extract.
    Giữ nguyên tên organic/sponsored — không đảo điều kiện.
    """
    sponsored_urls = {
        normalize_href_for_compare(s.destination_url)
        for s in sponsored
        if s.destination_url
    }
    kept: list[OrganicResult] = []
    for item in organic:
        if href_is_sponsored_ad_url(item.href):
            continue
        if normalize_href_for_compare(item.href) in sponsored_urls:
            continue
        kept.append(item)

    reranked: list[OrganicResult] = []
    for i, item in enumerate(kept, start=1):
        reranked.append(replace(item, rank=i))
    return reranked
