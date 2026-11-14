"""Click organic — kiểm tra Python + JS trước mỗi lần click (không click quảng cáo)."""

from __future__ import annotations

import os
import time

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

from .organic_parser import OrganicClickStat, OrganicResult
from .serp_ad_guard import (
    SponsoredAdClickBlockedError,
    assert_href_safe_for_organic_click,
)
from .serp_dom_scripts import script_click_organic_href_if_safe
from .serp_navigation import restore_serp_after_click


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    return int(v.strip())


def click_organic_results(
    page: Page,
    *,
    keyword: str,
    organic: list[OrganicResult],
    max_clicks: int,
    dwell_ms: int | None = None,
) -> list[OrganicClickStat]:
    if max_clicks <= 0 or not organic:
        return []

    dwell = dwell_ms if dwell_ms is not None else _env_int("ORGANIC_DWELL_MS", 2000)
    pause = _env_int("ORGANIC_CLICK_DELAY_MS", 800) / 1000.0
    stats: list[OrganicClickStat] = []
    serp_url = page.url
    click_script = script_click_organic_href_if_safe()

    targets = organic[:max_clicks]
    for item in targets:
        print(f"  [organic #{item.rank}] {item.title[:70]}...")
        status = "ok"
        err = ""
        final_url = ""

        try:
            assert_href_safe_for_organic_click(
                item.href,
                context=f"trước click organic #{item.rank}",
            )

            if page.url != serp_url:
                page.goto(serp_url, wait_until="domcontentloaded", timeout=45000)
                time.sleep(0.5)

            result = page.evaluate(click_script, item.href)
            if result.get("blocked"):
                raise SponsoredAdClickBlockedError(
                    f"DOM xác nhận sponsored_ad — không click: {item.href[:100]}"
                )
            if not result.get("clicked"):
                raise RuntimeError(
                    f"Không tìm thấy link organic an toàn trên SERP: {item.href[:80]}"
                )

            page.wait_for_load_state("domcontentloaded", timeout=45000)
            time.sleep(dwell / 1000.0)
            final_url = page.url
        except SponsoredAdClickBlockedError as e:
            status = "blocked_sponsored"
            err = str(e)[:200]
            final_url = page.url
        except PlaywrightTimeout as e:
            status = "timeout"
            err = str(e)[:200]
            final_url = page.url
        except Exception as e:
            status = "error"
            err = str(e)[:200]
            final_url = page.url

        stats.append(
            OrganicClickStat(
                keyword=keyword,
                rank=item.rank,
                title=item.title,
                serp_href=item.href,
                final_url=final_url,
                status=status,
                error=err,
                dwell_ms=dwell,
            )
        )

        if status == "blocked_sponsored":
            print(f"    ⚠ Bỏ qua — phát hiện quảng cáo, không click.")
            continue

        if status == "ok":
            restore_serp_after_click(page, serp_url)
        time.sleep(pause)

    return stats
