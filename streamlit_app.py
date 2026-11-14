"""
UI ToolClick — nhập từ khóa, cài đặt, xem log.

Chạy:
  streamlit run streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

from src.domain_filter import parse_domains_text
from src.google_region import locale_choice_labels, locale_label_for, parse_locale_choice
from src.proxy_config import parse_proxies_text
from src.job_runner import JobSettings, PROJECT_ROOT, launch_browser_window, stream_job
from src.ui_common import (
    ENV_PATH,
    env_bool,
    env_int,
    load_env_defaults,
    parse_keywords,
    save_env_from_settings,
)

st.set_page_config(
    page_title="ToolClick",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

def sidebar_settings(defaults: dict[str, str]) -> JobSettings:
    st.sidebar.header("Cài đặt")

    with st.sidebar.expander("Trình duyệt", expanded=True):
        headed = st.checkbox(
            "Hiện cửa sổ trình duyệt (--headed)",
            value=not env_bool(defaults.get("HEADLESS"), False),
        )
        _channels = ["chrome", "msedge", "auto", "chromium"]
        _ch_default = defaults.get("BROWSER_CHANNEL", "chrome")
        if _ch_default not in _channels:
            _ch_default = "chrome"
        browser_channel = st.selectbox(
            "Kênh trình duyệt (BROWSER_CHANNEL)",
            _channels,
            index=_channels.index(_ch_default),
        )
        use_persistent = st.checkbox(
            "Dùng profile cố định (USE_PERSISTENT_PROFILE)",
            value=env_bool(defaults.get("USE_PERSISTENT_PROFILE"), True),
        )
        user_data_dir = st.text_input(
            "Thư mục dữ liệu trình duyệt (USER_DATA_DIR)",
            value=defaults.get("USER_DATA_DIR", "browser-profile"),
        )

    with st.sidebar.expander("Google & thời gian chờ"):
        _loc_opts = locale_choice_labels()
        _loc_cur = locale_label_for(defaults.get("GOOGLE_LOCALE", "vi-VN"))
        if _loc_cur not in _loc_opts:
            _loc_opts = [_loc_cur, *_loc_opts]
        google_locale_pick = st.selectbox(
            "Ngôn ngữ / khu vực Google (GOOGLE_LOCALE)",
            options=_loc_opts,
            index=_loc_opts.index(_loc_cur),
            help="Chọn nhanh quốc gia có nhu cầu mua hàng cao, hoặc điền mã bên dưới.",
        )
        google_locale_custom = st.text_input(
            "Hoặc điền mã locale (vd. en-US, tr-TR) — để trống = dùng danh sách trên",
            value="",
        )
        google_locale = parse_locale_choice(
            google_locale_custom or google_locale_pick
        )
        search_delay_ms = st.number_input(
            "Chờ sau mỗi lần search, ms (SEARCH_DELAY_MS)",
            min_value=500,
            max_value=30000,
            step=100,
            value=env_int(defaults.get("SEARCH_DELAY_MS"), 2500),
        )
        captcha_wait_sec = st.number_input(
            "Chờ giải CAPTCHA tối đa, giây (CAPTCHA_WAIT_SEC)",
            min_value=30,
            max_value=900,
            step=10,
            value=env_int(defaults.get("CAPTCHA_WAIT_SEC"), 300),
        )

    organic_dwell_env = env_int(defaults.get("ORGANIC_DWELL_MS"), 2000)
    organic_click_delay = env_int(defaults.get("ORGANIC_CLICK_DELAY_MS"), 800)

    with st.sidebar.expander("Click quảng cáo"):
        st.caption(
            "Chạy từ UI luôn click quảng cáo khi bật ENABLE. "
            "Chỉ dùng môi trường được phép."
        )
        enable_sponsored = st.checkbox(
            "Bật click quảng cáo (ENABLE_SPONSORED_CLICK_TEST)",
            value=env_bool(defaults.get("ENABLE_SPONSORED_CLICK_TEST"), True),
        )
        max_sponsored = st.number_input(
            "Số quảng cáo tối đa mỗi SERP, 0 = click hết (--max-sponsored)",
            min_value=0,
            max_value=20,
            value=0,
        )
        sponsored_dwell_env = st.number_input(
            "Thời gian ở trang đích sau click, ms (SPONSORED_DWELL_MS)",
            min_value=500,
            max_value=60000,
            value=env_int(defaults.get("SPONSORED_DWELL_MS"), 1000),
        )
        sponsored_click_delay = st.number_input(
            "Nghỉ trước click tiếp theo, ms (SPONSORED_CLICK_DELAY_MS)",
            min_value=0,
            max_value=10000,
            value=env_int(defaults.get("SPONSORED_CLICK_DELAY_MS"), 300),
        )
        st.caption(
            "Mỗi vòng: click hết quảng cáo trên **cùng** SERP — mỗi ad **mở tab mới**, tab SERP giữ nguyên. "
            "Vòng 2+ khi bật lặp — tải SERP mới rồi click hết quảng cáo lại."
        )
        serp_repeat_enabled = st.checkbox(
            "Lặp SERP (vòng 2 trở lên)",
            value=env_int(defaults.get("SERP_REPEAT_COUNT"), 1) > 1,
            disabled=not enable_sponsored,
        )
        serp_repeat = st.number_input(
            "Số vòng SERP (--serp-repeat / SERP_REPEAT_COUNT)",
            min_value=1,
            max_value=10,
            value=max(1, env_int(defaults.get("SERP_REPEAT_COUNT"), 1)),
            disabled=not enable_sponsored or not serp_repeat_enabled,
            help="1 = chỉ SERP sau search đầu; 2+ = thêm vòng tải SERP mới.",
        )
        if not serp_repeat_enabled:
            serp_repeat = 1
        sponsored_dwell_override = st.checkbox(
            "Ghi đè thời gian ở trang đích (--sponsored-dwell-ms)",
            value=False,
        )
        sponsored_dwell_ms = None
        if sponsored_dwell_override:
            sponsored_dwell_ms = st.number_input(
                "Thời gian ở trang đích, ms (--sponsored-dwell-ms)",
                min_value=500,
                max_value=60000,
                value=sponsored_dwell_env,
            )

    with st.sidebar.expander("Proxy (nâng cao)"):
        _rotate_default = (defaults.get("PROXY_ROTATE_MODE") or "keyword").strip().lower()
        if _rotate_default in ("kw", "per_keyword"):
            _rotate_default = "keyword"
        elif _rotate_default not in ("keyword", "serp"):
            _rotate_default = "keyword"
        proxy_rotate_mode = st.selectbox(
            "Xoay proxy (PROXY_ROTATE_MODE)",
            ["keyword", "serp"],
            index=0 if _rotate_default == "keyword" else 1,
            format_func=lambda m: (
                "Theo từ khóa (ít CAPTCHA — khuyên dùng)"
                if m == "keyword"
                else "Theo từng SERP / vòng lặp"
            ),
        )
        proxy_persist_profile = st.checkbox(
            "Profile Chrome riêng từng proxy (PROXY_PERSIST_PROFILE)",
            value=env_bool(defaults.get("PROXY_PERSIST_PROFILE"), True),
        )
        proxy_warmup_all = st.checkbox(
            "Mở trình duyệt: làm nóng hết proxy (PROXY_WARMUP_ALL)",
            value=env_bool(defaults.get("PROXY_WARMUP_ALL"), False),
            help="Khi bấm «Mở cửa sổ trình duyệt», lần lượt mở từng proxy trong list.",
        )

    with st.sidebar.expander("Xuất file"):
        output_dir = st.text_input("Thư mục lưu kết quả (-o / output)", value="output")
        st.caption("Xuất: danh sách ads (.xlsx) và click ads (.csv).")
        export_format = "xlsx"
        debug = st.checkbox(
            "Gỡ lỗi: chụp màn hình khi 0 kết quả (--debug)",
            value=False,
        )

    return JobSettings(
        keywords=[],
        headed=headed,
        output_dir=output_dir,
        export_format=export_format,
        debug=debug,
        click_organic=False,
        max_organic=5,
        organic_dwell_ms=None,
        click_sponsored_test=enable_sponsored,
        max_sponsored=int(max_sponsored),
        sponsored_dwell_ms=int(sponsored_dwell_ms) if sponsored_dwell_ms is not None else None,
        google_locale=google_locale,
        search_delay_ms=int(search_delay_ms),
        browser_channel=browser_channel,
        use_persistent_profile=use_persistent,
        user_data_dir=user_data_dir,
        captcha_wait_sec=int(captcha_wait_sec),
        organic_click_delay_ms=int(organic_click_delay),
        enable_sponsored_click_test=enable_sponsored,
        sponsored_dwell_ms_env=int(sponsored_dwell_env),
        sponsored_click_delay_ms=int(sponsored_click_delay),
        organic_dwell_ms_env=int(organic_dwell_env),
        serp_repeat=int(serp_repeat) if enable_sponsored else None,
        allowed_domains=None,
        skip_domains=None,
        proxy_rotate_mode=proxy_rotate_mode,
        proxy_persist_profile=proxy_persist_profile,
        proxy_warmup_all=proxy_warmup_all,
    )


def main() -> None:
    defaults = load_env_defaults()

    st.title("ToolClick")
    st.markdown("Thu thập quảng cáo / organic Google — nhập từ khóa, chỉnh cài đặt bên trái, xem log bên dưới.")

    col_kw, col_actions = st.columns([3, 1])
    with col_kw:
        kw_text = st.text_area(
            "Từ khóa (mỗi dòng một từ, hoặc phân cách bằng dấu phẩy)",
            height=120,
            placeholder="hosting\nmua laptop văn phòng",
        )
        domain_text = st.text_area(
            "Domain chỉ được click (mỗi dòng hoặc dấu phẩy; để trống = click mọi quảng cáo)",
            height=80,
            placeholder="bluehost.com\ncontabo.com",
            value=defaults.get("ALLOWED_CLICK_DOMAINS", "").replace(",", "\n"),
        )
        skip_domain_text = st.text_area(
            "Domain không click (bỏ qua, không click; mỗi dòng hoặc dấu phẩy)",
            height=80,
            placeholder="example.com",
            value=defaults.get("SKIP_CLICK_DOMAINS", "").replace(",", "\n"),
        )
        st.markdown(
            "**Proxy** — [xem định dạng](#din-dang-proxy) · để trống = không dùng proxy"
        )
        _proxy_default = (defaults.get("PROXY_LIST") or "").replace("|", "\n").replace(",", "\n")
        proxy_text = st.text_area(
            "Danh sách proxy (PROXY_LIST)",
            height=80,
            placeholder="http://user:pass@host:8080\nsocks5://127.0.0.1:1080",
            value=_proxy_default,
            label_visibility="collapsed",
        )
        with st.expander("Định dạng proxy (PROXY_LIST)", expanded=False):
            st.markdown(
                '<span id="din-dang-proxy"></span>',
                unsafe_allow_html=True,
            )
            st.markdown(
                """
- Mỗi **dòng** (hoặc dấu phẩy / `|`) = một proxy.
- Ví dụ: `http://127.0.0.1:8080`, `http://user:pass@host:3128`, `socks5://host:1080`.
- **Xoay vòng:** mặc định `PROXY_ROTATE_MODE=keyword` — một IP cho cả từ khóa (+ mọi vòng lặp). Chọn `serp` ở sidebar nếu muốn đổi IP mỗi SERP.
- Không điền → trình duyệt **không** qua proxy (mặc định).
- Dùng proxy: bật **Hiện cửa sổ trình duyệt (--headed)** và giải CAPTCHA nếu Google yêu cầu.
- Lưu `.env`: nên dùng dạng `PROXY_LIST="http://user:pass@host:port"`.
- **CAPTCHA:** bật **headed**, tăng `CAPTCHA_WAIT_SEC`. Cookie theo proxy: `browser-profile/proxies/` khi `PROXY_PERSIST_PROFILE=true`.
- **Làm nóng hết proxy:** bật **PROXY_WARMUP_ALL** (sidebar) rồi **Mở cửa sổ trình duyệt** — giải CAPTCHA từng IP một lần.
                """
            )
    with col_actions:
        st.write("")
        st.write("")
        run_clicked = st.button("▶ Chạy", type="primary", use_container_width=True)
        open_browser_clicked = st.button(
            "Mở cửa sổ trình duyệt",
            use_container_width=True,
            help="Mở Chrome theo cài đặt sidebar + proxy (giải CAPTCHA trước khi Chạy).",
        )
        save_env = st.button("Lưu .env", use_container_width=True)
        clear_log = st.button("Xóa log", use_container_width=True)

    keywords = parse_keywords(kw_text)
    allowed_domains = parse_domains_text(domain_text)
    skip_domains = parse_domains_text(skip_domain_text)
    proxy_list = parse_proxies_text(proxy_text)
    cap_parts = [f"**{len(keywords)}** từ khóa"]
    if allowed_domains:
        cap_parts.append(f"**{len(allowed_domains)}** domain click")
    if skip_domains:
        cap_parts.append(f"**{len(skip_domains)}** domain không click")
    if proxy_list:
        cap_parts.append(f"**{len(proxy_list)}** proxy")
    st.caption("Đang có " + ", ".join(cap_parts) + ".")

    if "log_text" not in st.session_state:
        st.session_state.log_text = ""

    if clear_log:
        st.session_state.log_text = ""
        st.rerun()

    settings = sidebar_settings(defaults)
    settings.keywords = keywords
    settings.allowed_domains = allowed_domains or None
    settings.skip_domains = skip_domains or None
    settings.proxy_list = proxy_list or None

    if open_browser_clicked:
        launch_browser_window(settings)
        st.toast("Đã mở trình duyệt — xem cửa sổ console/Chrome.", icon="🌐")

    if save_env:
        save_env_from_settings(settings)
        st.sidebar.success(f"Đã lưu {ENV_PATH}")

    st.subheader("Log")
    log_box = st.empty()
    log_box.code(st.session_state.log_text or "(Chưa chạy job.)", language="text")

    if run_clicked:
        if not keywords:
            st.error("Nhập ít nhất một từ khóa.")
            return
        st.session_state.log_text = ""
        log_lines: list[str] = []
        with st.spinner("Đang chạy… (giải CAPTCHA trong cửa sổ trình duyệt nếu có)"):
            for chunk in stream_job(settings):
                log_lines.append(chunk)
                st.session_state.log_text = "".join(log_lines)
                log_box.code(st.session_state.log_text, language="text")

        out = PROJECT_ROOT / settings.output_dir
        if out.is_dir():
            st.success(f"Xong. Xem file trong: `{out}`")
            files = sorted(out.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)[:8]
            if files:
                st.write("File mới nhất:")
                for f in files:
                    st.text(f.name)


if __name__ == "__main__":
    main()
