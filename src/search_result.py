from __future__ import annotations

from dataclasses import dataclass, field

from .organic_parser import OrganicClickStat, OrganicResult
from .sponsored_clicker import SponsoredClickStat
from .sponsored_parser import SponsoredResult


@dataclass
class SerpRoundStat:
    round: int
    sponsored_found: int
    sponsored_clicks_attempted: int
    sponsored_clicks_ok: int


@dataclass
class KeywordSearchResult:
    keyword: str
    sponsored: list[SponsoredResult]
    organic: list[OrganicResult]
    organic_clicks: list[OrganicClickStat]
    sponsored_clicks: list[SponsoredClickStat]
    serp_round_stats: list[SerpRoundStat] = field(default_factory=list)

    @property
    def sponsored_found_total(self) -> int:
        """Số quảng cáo thấy trên mọi vòng SERP (khớp click theo từng vòng)."""
        if self.serp_round_stats:
            return sum(r.sponsored_found for r in self.serp_round_stats)
        return len(self.sponsored)
