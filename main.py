"""
Tool thu thập quảng cáo + organic Google theo từ khóa.

- Mặc định không click quảng cáo.
- Click organic: --click-organic
- Click quảng cáo (test): ENABLE_SPONSORED_CLICK_TEST=true + --click-sponsored-test
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import sys as _sys

from src.console_io import ensure_utf8_stdio

ensure_utf8_stdio()

from src.google_scraper import (
    GoogleSponsoredScraper,
    export_results,
    export_sponsored_click_stats,
)
from src.domain_filter import parse_domains_env, parse_domains_text
from src.proxy_config import parse_proxies_env, proxy_label
from src.serp_ad_guard import sponsored_click_test_enabled


def _warn_if_not_venv() -> None:
    if getattr(_sys, "frozen", False):
        return
    if getattr(_sys, "prefix", "") == getattr(_sys, "base_prefix", ""):
        print(
            "Cảnh báo: bạn đang chạy Python global, không phải .venv.\n"
            "  PowerShell: .\\.venv\\Scripts\\Activate.ps1\n"
            "  Git Bash:   source .venv/Scripts/activate\n"
        )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Thu thập quảng cáo + organic Google theo từ khóa.")
    p.add_argument("-k", "--keywords", nargs="+", required=True)
    p.add_argument("--headed", action="store_true")
    p.add_argument("-o", "--output-dir", type=Path, default=Path("output"))
    p.add_argument("--format", choices=("csv", "xlsx", "both"), default="both")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--click-organic", action="store_true")
    p.add_argument("--max-organic", type=int, default=5)
    p.add_argument("--organic-dwell-ms", type=int, default=None)
    p.add_argument(
        "--click-sponsored-test",
        action="store_true",
        help="Click quảng cáo Sponsored (cần ENABLE_SPONSORED_CLICK_TEST=true trong .env).",
    )
    p.add_argument(
        "--max-sponsored",
        type=int,
        default=0,
        help="Số quảng cáo tối đa để click; 0 = click hết sponsored_found.",
    )
    p.add_argument("--sponsored-dwell-ms", type=int, default=None)
    p.add_argument(
        "--serp-repeat",
        type=int,
        default=None,
        help="Số lần tải SERP mới (round 1 = SERP sau search đầu). Mặc định: SERP_REPEAT_COUNT trong .env.",
    )
    p.add_argument(
        "--allowed-domains",
        nargs="*",
        default=None,
        metavar="DOMAIN",
        help="Chỉ click quảng cáo thuộc các domain này (vd. bluehost.com). Để trống = mọi quảng cáo.",
    )
    p.add_argument(
        "--skip-domains",
        nargs="*",
        default=None,
        metavar="DOMAIN",
        help="Không click quảng cáo thuộc các domain này.",
    )
    return p.parse_args()


def main() -> None:
    _warn_if_not_venv()
    args = parse_args()

    if args.click_sponsored_test:
        if not sponsored_click_test_enabled():
            print(
                "Từ chối: --click-sponsored-test cần ENABLE_SPONSORED_CLICK_TEST=true trong .env\n"
                "Chỉ dùng để test quảng cáo của bạn / môi trường được phép.",
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            "*** TEST CLICK QUẢNG CÁO BẬT ***\n"
            "Có thể tính phí Ads / vi phạm chính sách nếu lạm dụng.\n"
        )

    if (args.click_organic or args.click_sponsored_test) and not args.headed:
        print("Gợi ý: dùng --headed khi click để theo dõi và giảm CAPTCHA.\n")

    debug_dir = args.output_dir / "debug" if args.debug else None
    if args.allowed_domains is not None:
        allowed_domains = parse_domains_text(",".join(args.allowed_domains))
    else:
        allowed_domains = parse_domains_env(os.getenv("ALLOWED_CLICK_DOMAINS"))
    if args.skip_domains is not None:
        skip_domains = parse_domains_text(",".join(args.skip_domains))
    else:
        skip_domains = parse_domains_env(os.getenv("SKIP_CLICK_DOMAINS"))
    if allowed_domains and args.click_sponsored_test:
        print(f"Chỉ click quảng cáo domain: {', '.join(allowed_domains)}\n")
    if skip_domains and args.click_sponsored_test:
        print(f"Không click domain: {', '.join(skip_domains)}\n")

    proxy_lines = parse_proxies_env(os.getenv("PROXY_LIST"))
    if proxy_lines:
        print(
            "Proxy xoay vòng theo SERP:",
            ", ".join(proxy_label(p) for p in proxy_lines),
            "\n",
        )

    scraper = GoogleSponsoredScraper(
        headless=not args.headed,
        debug_dir=debug_dir,
        click_organic=args.click_organic,
        max_organic_clicks=args.max_organic if args.click_organic else 0,
        organic_dwell_ms=args.organic_dwell_ms,
        click_sponsored_test=args.click_sponsored_test,
        max_sponsored_clicks=args.max_sponsored if args.click_sponsored_test else 0,
        sponsored_dwell_ms=args.sponsored_dwell_ms,
        serp_repeat=args.serp_repeat,
        allowed_click_domains=allowed_domains,
        skip_click_domains=skip_domains,
        proxy_lines=proxy_lines,
    )

    all_sponsored = []
    all_organic = []
    all_organic_clicks = []
    all_sponsored_clicks = []
    stats_by_keyword: dict[str, dict] = {}

    for kw in args.keywords:
        print(f"Đang tìm kiếm: {kw!r} ...")
        try:
            result = scraper.run_search(kw)
        except RuntimeError as e:
            print(f"Lỗi: {e}", file=sys.stderr)
            sys.exit(1)
        all_sponsored.extend(result.sponsored)
        all_organic.extend(result.organic)
        all_organic_clicks.extend(result.organic_clicks)
        all_sponsored_clicks.extend(result.sponsored_clicks)

        ok_o = sum(1 for c in result.organic_clicks if c.status == "ok")
        ok_s = sum(1 for c in result.sponsored_clicks if c.status == "ok")
        round_detail = [
            {
                "round": r.round,
                "sponsored_found": r.sponsored_found,
                "sponsored_clicks_attempted": r.sponsored_clicks_attempted,
                "sponsored_clicks_ok": r.sponsored_clicks_ok,
            }
            for r in result.serp_round_stats
        ]
        found_ads = result.sponsored_found_total
        stats_by_keyword[kw] = {
            "sponsored_found": found_ads,
            "organic_found": len(result.organic),
            "organic_clicks_attempted": len(result.organic_clicks),
            "organic_clicks_ok": ok_o,
            "sponsored_clicks_attempted": len(result.sponsored_clicks),
            "sponsored_clicks_ok": ok_s,
            "serp_rounds": round_detail,
        }
        print(f"  → Quảng cáo: {found_ads} | Organic: {len(result.organic)}")
        if args.click_organic:
            print(f"  → Click organic: {ok_o}/{len(result.organic_clicks)} ok")
        if args.click_sponsored_test:
            print(f"  → Click quảng cáo: {ok_s}/{len(result.sponsored_clicks)} ok")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")

    xlsx_path = args.output_dir / f"sponsored_{stamp}.xlsx"
    export_results(all_sponsored, csv_path=None, xlsx_path=xlsx_path)
    print(f"Đã lưu danh sách quảng cáo: {xlsx_path}")
    if all_sponsored_clicks:
        sp_path = args.output_dir / f"sponsored_clicks_{stamp}.csv"
        export_sponsored_click_stats(all_sponsored_clicks, csv_path=sp_path)
        print(f"Đã lưu click quảng cáo: {sp_path}")

    ad_ok = sum(1 for c in all_sponsored_clicks if c.status == "ok")
    summary = {
        "total_sponsored_found": sum(
            int(v.get("sponsored_found") or 0) for v in stats_by_keyword.values()
        ),
        "total_organic_found": len(all_organic),
        "organic_clicks_ok": sum(1 for c in all_organic_clicks if c.status == "ok"),
        "sponsored_clicks_ok": ad_ok,
        "ad_clicks_performed": ad_ok if sponsored_click_test_enabled() else 0,
        "enable_sponsored_click_test": sponsored_click_test_enabled(),
        "allowed_click_domains": allowed_domains,
        "skip_click_domains": skip_domains,
        "proxy_list": proxy_lines,
        "by_keyword": stats_by_keyword,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
