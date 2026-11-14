# ToolClick — Chạy local và build .exe

Cần **Google Chrome** (hoặc Edge) đã cài trên máy. Bản `.exe` **không** kèm Chromium Playwright.

PowerShell nếu báo *running scripts is disabled*, dùng:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Hoặc gọi script bằng:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run_ui.ps1
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

---

## 1. Cài đặt (một lần)

```powershell
cd D:\Project\ToolClick
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

Script tạo `.venv`, cài thư viện, cài Chromium Playwright, copy `config.example.env` → `.env` nếu chưa có.

Kích hoạt venv (tùy chọn, khi chạy `python` trực tiếp):

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 2. Chạy local (cửa sổ app)

```powershell
cd D:\Project\ToolClick
powershell -ExecutionPolicy Bypass -File .\run_ui.ps1
```

Hoặc:

```powershell
.\.venv\Scripts\python.exe desktop_app.py
```

- Tab **Công việc**: từ khóa, Domain click, Domain không click, proxy, Chạy / Dừng / Mở trình duyệt.
- Tab **Cài đặt**: Chrome, locale, click ads, proxy, **bản quyền** — **Lưu cài đặt (.env)**.

### Key bản quyền (Laravel)

```powershell
cd license-server
php artisan migrate
php artisan serve
```

Mở http://127.0.0.1:8000 — email `admin@toolclick.local` / mật khẩu `admin123`. Tạo key, giới hạn máy và record/ngày. Trên ToolClick dán key rồi **Kích hoạt key trên máy này**. Chạy job sẽ bị chặn nếu key hết hạn, đủ số máy, hoặc hết hạn mức ngày.
- Bật **Hiện cửa sổ Chrome** khi cần giải CAPTCHA.
- Click quảng cáo: bật `ENABLE_SPONSORED_CLICK_TEST` (hoặc checkbox trên UI).

Kết quả mỗi job trong thư mục `output\`:

- `sponsored_….xlsx` — danh sách quảng cáo
- `sponsored_clicks_….csv` — lịch sử click (nếu có click)

`.env`, `output\`, `browser-profile\` nằm cạnh project khi chạy source.

### CLI (không UI)

```powershell
.\.venv\Scripts\python.exe main.py -k "tu khoa" --headed --click-sponsored-test --max-sponsored 0 --serp-repeat 1
```

---

## 3. Build file .exe

Đóng ToolClick nếu đang mở.

```powershell
cd D:\Project\ToolClick
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Kết quả: `dist\ToolClick\ToolClick.exe`

Phân phối: **zip cả thư mục** `dist\ToolClick` (gồm `_internal`), không chỉ file `.exe`.

Chạy bản đóng gói: double-click `ToolClick.exe`.  
`.env`, `output\`, `browser-profile\` nằm **cạnh** file exe.

CLI từ exe:

```text
ToolClick.exe --toolclick-main -k "tu khoa" --headed
```

---

## 4. Proxy (tùy chọn)

Ô **Proxy** trên UI hoặc `PROXY_LIST` trong `.env`. Mọi nhà cung cấp, ví dụ:

```text
http://user:pass@host:port
socks5://127.0.0.1:1080
```

Không riêng một hãng. Nên **headed** + giải CAPTCHA lần đầu; cookie lưu theo proxy trong `browser-profile/proxies/`.
