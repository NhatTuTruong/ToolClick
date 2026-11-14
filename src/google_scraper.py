"""Tìm kiếm Google và thu thập kết quả quảng cáo (chỉ đọc DOM, không click quảng cáo)."""

from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeout,
    sync_playwright,
)

from .browser_session import open_browser_session, persist_proxy_storage
from .google_region import google_home_url, google_search_url
from .captcha import is_google_captcha, wait_for_captcha_clear
from .organic_clicker import click_organic_results
from .organic_parser import (
    OrganicClickStat,
    OrganicResult,
    extract_organic_from_page,
    finalize_organic_list,
)
from .serp_navigation import reload_serp_for_ads
from .sponsored_clicker import SponsoredClickStat, click_sponsored_on_current_serp
from .search_result import KeywordSearchResult, SerpRoundStat
from .domain_filter import parse_domains_env
from .proxy_config import (
    ProxyRotator,
    is_proxy_connection_error,
    parse_proxies_env,
    proxy_error_hint,
    proxy_label,
    proxy_rotate_mode,
)
from .sponsored_parser import SponsoredResult, extract_sponsored_from_page

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


class GoogleSponsoredScraper:
    def __init__(
        self,
        *,
        headless: bool | None = None,
        locale: str | None = None,
        delay_ms: int | None = None,
        debug_dir: Path | None = None,
        click_organic: bool = False,
        max_organic_clicks: int = 0,
        organic_dwell_ms: int | None = None,
        click_sponsored_test: bool = False,
        max_sponsored_clicks: int = 0,
        sponsored_dwell_ms: int | None = None,
        serp_repeat: int | None = None,
        allowed_click_domains: list[str] | None = None,
        skip_click_domains: list[str] | None = None,
        proxy_lines: list[str] | None = None,
        proxy_rotator: ProxyRotator | None = None,
    ) -> None:
        self.headless = headless if headless is not None else _env_bool("HEADLESS", True)
        self.locale = locale or os.getenv("GOOGLE_LOCALE", "vi-VN")
        self.delay_ms = delay_ms or int(os.getenv("SEARCH_DELAY_MS", "2500"))
        self.debug_dir = debug_dir
        self.click_organic = click_organic
        self.max_organic_clicks = max_organic_clicks
        self.organic_dwell_ms = organic_dwell_ms
        self.click_sponsored_test = click_sponsored_test
        self.max_sponsored_clicks = max_sponsored_clicks
        self.sponsored_dwell_ms = sponsored_dwell_ms
        self.serp_repeat = serp_repeat if serp_repeat is not None else int(
            os.getenv("SERP_REPEAT_COUNT", "1")
        )
        if allowed_click_domains is not None:
            self.allowed_click_domains = allowed_click_domains
        else:
            self.allowed_click_domains = parse_domains_env(
                os.getenv("ALLOWED_CLICK_DOMAINS")
            )
        if skip_click_domains is not None:
            self.skip_click_domains = skip_click_domains
        else:
            self.skip_click_domains = parse_domains_env(
                os.getenv("SKIP_CLICK_DOMAINS")
            )
        profile = os.getenv("USER_DATA_DIR", "browser-profile")
        self.user_data_dir = Path(profile)
        self._active_proxy: dict[str, str] | None = None
        if proxy_rotator is not None:
            self.proxy_rotator = proxy_rotator
        elif proxy_lines is not None:
            self.proxy_rotator = ProxyRotator.from_lines(proxy_lines)
        else:
            self.proxy_rotator = ProxyRotator.from_lines(
                parse_proxies_env(os.getenv("PROXY_LIST"))
            )

    def search_keyword(self, keyword: str) -> list[SponsoredResult]:
        return self.run_search(keyword).sponsored

    def run_search(self, keyword: str) -> KeywordSearchResult:
        keyword = keyword.strip()
        if not keyword:
            return KeywordSearchResult(
                keyword="",
                sponsored=[],
                organic=[],
                organic_clicks=[],
                sponsored_clicks=[],
                serp_round_stats=[],
            )

        rounds = max(1, self.serp_repeat) if self.click_sponsored_test else 1
        if self.proxy_rotator and self.proxy_rotator.enabled:
            mode = proxy_rotate_mode()
            # Một proxy hoặc xoay theo từ khóa: một Chrome / keyword (ít CAPTCHA hơn).
            if self.proxy_rotator.count == 1 or mode == "keyword":
                _raw, proxy_cfg = self.proxy_rotator.next()
                if mode == "keyword" and self.proxy_rotator.count > 1:
                    print(f"  [proxy] Che do keyword — giu {proxy_label(_raw)} cho ca tu khoa nay.")
                return self._run_search_one_browser(
                    keyword, rounds, proxy=proxy_cfg
                )
            return self._run_search_with_proxy_rotation(keyword, rounds)
        return self._run_search_one_browser(keyword, rounds)

    def _run_search_one_browser(
        self,
        keyword: str,
        rounds: int,
        *,
        proxy: dict | None = None,
    ) -> KeywordSearchResult:
        self._active_proxy = proxy
        with sync_playwright() as p:
            session = open_browser_session(
                p,
                headless=self.headless,
                user_data_dir=self.user_data_dir,
                locale=self.locale,
                proxy=proxy,
            )
            page = session.context.pages[0] if session.context.pages else session.context.new_page()
            try:
                return self._finish_keyword_on_page(
                    page, keyword=keyword, rounds=rounds, proxy_note=""
                )
            except PlaywrightTimeout as e:
                raise RuntimeError(f"Hết thời gian chờ khi tìm '{keyword}': {e}") from e
            finally:
                session.close()
                self._active_proxy = None

    def _run_search_with_proxy_rotation(
        self, keyword: str, rounds: int
    ) -> KeywordSearchResult:
        assert self.proxy_rotator is not None
        sponsored_all: list[SponsoredResult] = []
        organic: list[OrganicResult] = []
        clicks: list[OrganicClickStat] = []
        sponsored_clicks: list[SponsoredClickStat] = []
        serp_round_stats: list[SerpRoundStat] = []

        proxy_attempts = max(1, self.proxy_rotator.count)

        for round_num in range(1, rounds + 1):
            prefix = f"[serp-round {round_num}] " if round_num > 1 or rounds > 1 else ""
            last_err: Exception | None = None
            last_raw = ""

            for attempt in range(proxy_attempts):
                raw, proxy_cfg = self.proxy_rotator.next()
                last_raw = raw
                note = proxy_label(raw)
                print(f"  {prefix}[proxy] {note}")

                self._active_proxy = proxy_cfg
                with sync_playwright() as p:
                    session = open_browser_session(
                        p,
                        headless=self.headless,
                        user_data_dir=self.user_data_dir,
                        locale=self.locale,
                        proxy=proxy_cfg,
                    )
                    page = (
                        session.context.pages[0]
                        if session.context.pages
                        else session.context.new_page()
                    )
                    try:
                        self._perform_google_search(page, keyword)
                        sponsored = self._extract_after_search(page, keyword)
                        for item in sponsored:
                            item.serp_round = round_num
                        sponsored_all.extend(sponsored)
                        if round_num == 1:
                            organic_raw = extract_organic_from_page(page, keyword)
                            organic = finalize_organic_list(organic_raw, sponsored)
                            if self.click_organic and self.max_organic_clicks > 0:
                                clicks = click_organic_results(
                                    page,
                                    keyword=keyword,
                                    organic=organic,
                                    max_clicks=self.max_organic_clicks,
                                    dwell_ms=self.organic_dwell_ms,
                                )
                        elif round_num > 1:
                            print(
                                f"  [serp-round {round_num}] SERP mới (proxy xoay vòng)..."
                            )

                        if self.click_sponsored_test:
                            round_clicks = click_sponsored_on_current_serp(
                                page,
                                keyword=keyword,
                                sponsored=sponsored,
                                max_clicks=self.max_sponsored_clicks,
                                dwell_ms=self.sponsored_dwell_ms,
                                serp_round=round_num,
                                allowed_domains=self.allowed_click_domains,
                                skip_domains=self.skip_click_domains,
                            )
                            sponsored_clicks.extend(round_clicks)
                            ok_r = sum(1 for c in round_clicks if c.status == "ok")
                            serp_round_stats.append(
                                SerpRoundStat(
                                    round=round_num,
                                    sponsored_found=len(sponsored),
                                    sponsored_clicks_attempted=len(round_clicks),
                                    sponsored_clicks_ok=ok_r,
                                )
                            )
                        last_err = None
                        break
                    except PlaywrightTimeout as e:
                        last_err = e
                        if attempt + 1 < proxy_attempts:
                            print(
                                f"  [proxy] Timeout qua {note} — thử proxy kế tiếp..."
                            )
                            continue
                        raise RuntimeError(
                            f"Hết thời gian chờ khi tìm '{keyword}' (proxy {note}): {e}"
                        ) from e
                    except (PlaywrightError, OSError) as e:
                        last_err = e
                        if is_proxy_connection_error(e) and attempt + 1 < proxy_attempts:
                            print(
                                f"  [proxy] Lỗi kết nối {note}: {str(e)[:120]}"
                                f" — thử proxy kế tiếp..."
                            )
                            continue
                        if is_proxy_connection_error(e):
                            raise RuntimeError(proxy_error_hint(last_raw)) from e
                        raise
                    finally:
                        session.close()
                        self._active_proxy = None

            if last_err is not None:
                raise RuntimeError(proxy_error_hint(last_raw)) from last_err

        return KeywordSearchResult(
            keyword=keyword,
            sponsored=sponsored_all,
            organic=organic,
            organic_clicks=clicks,
            sponsored_clicks=sponsored_clicks,
            serp_round_stats=serp_round_stats,
        )

    def _extract_after_search(
        self, page, keyword: str
    ) -> list[SponsoredResult]:
        sponsored = extract_sponsored_from_page(page, keyword)
        organic_raw = extract_organic_from_page(page, keyword)
        organic = finalize_organic_list(organic_raw, sponsored)
        if not sponsored and not organic and self.debug_dir:
            self._save_debug(page, keyword)
        if is_google_captcha(page):
            wait_for_captcha_clear(page, headed=not self.headless)
            sponsored = extract_sponsored_from_page(page, keyword)
        return sponsored

    def _finish_keyword_on_page(
        self,
        page,
        *,
        keyword: str,
        rounds: int,
        proxy_note: str,
    ) -> KeywordSearchResult:
        self._perform_google_search(page, keyword)
        sponsored = self._extract_after_search(page, keyword)
        organic_raw = extract_organic_from_page(page, keyword)
        organic = finalize_organic_list(organic_raw, sponsored)
        if is_google_captcha(page):
            organic_raw = extract_organic_from_page(page, keyword)
            organic = finalize_organic_list(organic_raw, sponsored)

        clicks: list[OrganicClickStat] = []
        if self.click_organic and self.max_organic_clicks > 0:
            clicks = click_organic_results(
                page,
                keyword=keyword,
                organic=organic,
                max_clicks=self.max_organic_clicks,
                dwell_ms=self.organic_dwell_ms,
            )

        sponsored_clicks: list[SponsoredClickStat] = []
        serp_round_stats: list[SerpRoundStat] = []
        sponsored_all: list[SponsoredResult] = []
        for item in sponsored:
            item.serp_round = 1

        if self.click_sponsored_test:
            for round_num in range(1, rounds + 1):
                if round_num > 1:
                    print(f"  [serp-round {round_num}] Tải SERP mới (lặp lại)...")
                    reload_serp_for_ads(
                        page, keyword=keyword, fallback_serp_url=page.url
                    )
                    sponsored = extract_sponsored_from_page(page, keyword)
                    for item in sponsored:
                        item.serp_round = round_num
                sponsored_all.extend(sponsored)

                round_clicks = click_sponsored_on_current_serp(
                    page,
                    keyword=keyword,
                    sponsored=sponsored,
                    max_clicks=self.max_sponsored_clicks,
                    dwell_ms=self.sponsored_dwell_ms,
                    serp_round=round_num,
                    allowed_domains=self.allowed_click_domains,
                    skip_domains=self.skip_click_domains,
                )
                sponsored_clicks.extend(round_clicks)
                ok_r = sum(1 for c in round_clicks if c.status == "ok")
                serp_round_stats.append(
                    SerpRoundStat(
                        round=round_num,
                        sponsored_found=len(sponsored),
                        sponsored_clicks_attempted=len(round_clicks),
                        sponsored_clicks_ok=ok_r,
                    )
                )

        _ = proxy_note
        if not self.click_sponsored_test:
            sponsored_all = list(sponsored)
        return KeywordSearchResult(
            keyword=keyword,
            sponsored=sponsored_all,
            organic=organic,
            organic_clicks=clicks,
            sponsored_clicks=sponsored_clicks,
            serp_round_stats=serp_round_stats,
        )

    def _uses_proxy(self) -> bool:
        return self.proxy_rotator is not None and self.proxy_rotator.enabled

    def _nav_timeout_ms(self) -> int:
        if self._uses_proxy():
            return int(os.getenv("PROXY_NAV_TIMEOUT_MS", "90000"))
        return 60000

    def _search_delay_ms(self) -> int:
        if self._uses_proxy():
            cap = int(os.getenv("PROXY_SEARCH_DELAY_MS", "1200"))
            return min(self.delay_ms, cap)
        return self.delay_ms

    def _save_proxy_cookies(self, page) -> None:
        if not self._active_proxy:
            return
        persist_proxy_storage(
            page,
            user_data_dir=self.user_data_dir,
            proxy=self._active_proxy,
        )

    def _wait_serp_after_nav(self, page) -> None:
        """Sau goto qua proxy: chờ khung SERP, không chờ domcontentloaded full (Google + proxy rất chậm)."""
        try:
            page.wait_for_selector(
                "#search, #rso, #tads, div[data-async-context]",
                timeout=int(os.getenv("PROXY_SERP_WAIT_MS", "20000")),
            )
        except PlaywrightTimeout:
            pass

    def _perform_google_search(self, page, keyword: str) -> None:
        nav_ms = self._nav_timeout_ms()
        if self._uses_proxy():
            # Qua proxy: vào thẳng SERP (google.com/ncr hay treo trên Chrome).
            url = google_search_url(keyword, self.locale)
            page.goto(url, wait_until="commit", timeout=nav_ms)
            self._wait_serp_after_nav(page)
            wait_for_captcha_clear(page, headed=not self.headless)
            self._save_proxy_cookies(page)
        else:
            page.goto(
                google_home_url(self.locale),
                wait_until="domcontentloaded",
                timeout=nav_ms,
            )
            wait_for_captcha_clear(page, headed=not self.headless)
            self._accept_consent_if_present(page)
            wait_for_captcha_clear(page, headed=not self.headless)

            box = page.locator('textarea[name="q"], input[name="q"]').first
            box.wait_for(state="visible", timeout=20000)
            box.click()
            box.fill("")
            page.keyboard.type(keyword, delay=80)
            page.keyboard.press("Enter")

        if not self._uses_proxy():
            try:
                page.wait_for_selector(
                    "#search, #rso, div[data-async-context]",
                    timeout=25000,
                )
            except PlaywrightTimeout:
                pass
            try:
                page.wait_for_load_state("domcontentloaded", timeout=30000)
            except PlaywrightTimeout:
                pass
        time.sleep(self._search_delay_ms() / 1000.0)
        wait_for_captcha_clear(page, headed=not self.headless)
        self._save_proxy_cookies(page)
        self._accept_consent_if_present(page)
        try:
            page.wait_for_selector(
                "#tads, #tadsb, [data-text-ad], .uEierd",
                timeout=8000,
            )
        except PlaywrightTimeout:
            pass
        page.evaluate("window.scrollBy(0, 450)")
        time.sleep(0.5)
        page.evaluate("window.scrollBy(0, document.body.scrollHeight * 0.35)")
        time.sleep(0.45)
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(0.25)
        self._save_proxy_cookies(page)

    def _save_debug(self, page, keyword: str) -> None:
        assert self.debug_dir is not None
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in keyword)[:40]
        stamp = int(time.time())
        png = self.debug_dir / f"debug_{safe}_{stamp}.png"
        html = self.debug_dir / f"debug_{safe}_{stamp}.html"
        page.screenshot(path=str(png), full_page=True)
        html.write_text(page.content(), encoding="utf-8")
        print(f"  [debug] 0 quảng cáo — đã lưu {png.name}, {html.name}")

    @staticmethod
    def _accept_consent_if_present(page) -> None:
        for sel in (
            'button:has-text("Accept all")',
            'button:has-text("Tôi đồng ý")',
            'button:has-text("Đồng ý")',
            'button:has-text("Agree")',
            'button:has-text("Tất cả")',
        ):
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=800):
                    btn.click()
                    time.sleep(0.5)
                    return
            except PlaywrightTimeout:
                continue


def export_results(
    rows: list[SponsoredResult],
    *,
    csv_path: Path | None = None,
    xlsx_path: Path | None = None,
) -> None:
    _export_table(rows, csv_path=csv_path, xlsx_path=xlsx_path)


def export_organic_tables(
    organic: list[OrganicResult],
    clicks: list[OrganicClickStat],
    *,
    organic_csv: Path | None = None,
    clicks_csv: Path | None = None,
) -> None:
    if organic_csv:
        _export_table(organic, csv_path=organic_csv, xlsx_path=None)
    if clicks_csv and clicks:
        _export_table(clicks, csv_path=clicks_csv, xlsx_path=None)


def export_sponsored_click_stats(clicks: list[SponsoredClickStat], *, csv_path: Path) -> None:
    if clicks:
        _export_table(clicks, csv_path=csv_path, xlsx_path=None)


def _export_table(rows, *, csv_path: Path | None, xlsx_path: Path | None) -> None:
    import pandas as pd

    data = [r.to_row() for r in rows]
    df = pd.DataFrame(data)

    if csv_path:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    if xlsx_path:
        xlsx_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(xlsx_path, index=False, engine="openpyxl")
