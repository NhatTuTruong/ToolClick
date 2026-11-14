"""Trích xuất quảng cáo Sponsored — chỉ anchorIsSponsoredAd == true (serp_dom_scripts)."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

from .serp_ad_guard import SPONSORED_TEXT_LABELS
from .serp_dom_scripts import script_extract_sponsored_anchors

# Re-export cho tài liệu / tương thích
SPONSORED_LABELS = SPONSORED_TEXT_LABELS


@dataclass
class SponsoredResult:
    keyword: str
    rank: int
    title: str
    display_url: str
    destination_url: str
    label: str
    snippet: str
    serp_round: int = 1

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_sponsored_from_page(page, keyword: str) -> list[SponsoredResult]:
    raw: list[dict] = page.evaluate(script_extract_sponsored_anchors())
    out: list[SponsoredResult] = []
    for i, item in enumerate(raw, start=1):
        dest = item.get("destination_url") or ""
        if not dest:
            continue
        out.append(
            SponsoredResult(
                keyword=keyword,
                rank=i,
                title=_normalize(item.get("title", "")),
                display_url=_normalize(item.get("display_url", "")),
                destination_url=dest,
                label=_normalize(item.get("label", "")),
                snippet=_normalize(item.get("snippet", "")),
            )
        )
    return out
