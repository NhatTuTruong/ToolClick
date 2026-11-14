# ToolClick — Thu thập quảng cáo Google (Sponsored)

Tool Python dùng **Playwright** mô phỏng trình duyệt, tìm kiếm Google theo từ khóa, lọc các block có nhãn **Sponsored** / **Quảng cáo**, xuất **CSV/Excel** và file thống kê JSON.

## Không hỗ trợ click quảng cáo hàng loạt

Yêu cầu “click hết quảng cáo” tương ứng **gian lận click (click fraud)** — vi phạm [Google Ads policies](https://support.google.com/adspolicy/answer/6020954) và gây thiệt hại cho nhà quảng cáo. Repo này **chỉ scrape metadata** (tiêu đề, URL hiển thị, link đích), **không** tự động click `/aclk`.

Nếu bạn cần kiểm tra **quảng cáo của chính mình**, dùng Google Ads Preview Tool hoặc tài khoản test trong Google Ads.

## Cài đặt

```powershell
cd d:\Project\ToolClick
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## Chạy

```powershell
python main.py -k "dịch vụ seo" "mua laptop" --headed
```

Kết quả trong thư mục `output/`:

- `sponsored_*.csv` / `sponsored_*.xlsx` — danh sách quảng cáo
- `stats_*.json` — số lượng tìm thấy theo từ khóa

## Cấu hình (tùy chọn)

Sao chép `config.example.env` → `.env`:

- `HEADLESS=true|false`
- `GOOGLE_LOCALE=vi-VN`
- `SEARCH_DELAY_MS=1500`

## Lưu ý kỹ thuật

- Google thay DOM thường xuyên; parser trong `src/sponsored_parser.py` có thể cần cập nhật selector.
- Google có thể hiện CAPTCHA nếu truy vấn quá dày — hãy giảm tần suất và tuân thủ robots/điều khoản dịch vụ.
- Selenium / undetected-chromedriver có thể thay Playwright; luồng nghiệp vụ tương tự.

## Build file .exe (Windows)

Cần **Google Chrome** trên máy chạy (Playwright dùng kênh `chrome`, không gói Chromium).

```powershell
.\build_exe.ps1
```

Kết quả: `dist\ToolClick\ToolClick.exe` (kèm thư mục `_internal`). Zip cả `dist\ToolClick` để copy sang máy khác.

- Chạy `ToolClick.exe` → **cửa sổ ứng dụng** (không mở trình duyệt / không port 8501).
- `.env`, `output\`, `browser-profile\` nằm **cạnh** file `.exe`.
- Dev từ source: `python desktop_app.py` hoặc `.\run_ui.ps1`. Streamlit cũ: `streamlit run streamlit_app.py`.

## Cấu trúc

```
main.py
toolclick_entry.py       # Entry PyInstaller
src/google_scraper.py    # Playwright + tìm kiếm
src/sponsored_parser.py  # Nhận diện nhãn quảng cáo
requirements.txt
```
