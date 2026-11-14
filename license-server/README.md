# ToolClick License Server (Laravel)

Quản lý **key bản quyền** và giới hạn **số máy** / **record mỗi ngày**.

## Chạy local

Cần **MySQL** (WAMP mặc định `127.0.0.1:3306`, user `root`, mật khẩu trống). Tạo database:

```sql
CREATE DATABASE toolclick_license CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

```bash
cd license-server
copy .env.example .env   # nếu chưa có
php artisan key:generate
php artisan migrate
php artisan serve
```

Mở http://127.0.0.1:8000 — đăng nhập:

- Email: `admin@toolclick.local`
- Mật khẩu: `admin123`

Đổi trong `.env`:

```
ADMIN_EMAIL=admin@toolclick.local
ADMIN_PASSWORD=admin123
LICENSE_API_SECRET=
```

Nếu `LICENSE_API_SECRET` có giá trị, client ToolClick phải gửi cùng secret (`X-License-Secret`).

## ToolClick

Tab **Cài đặt → Bản quyền**:

- Máy chủ: `http://127.0.0.1:8000`
- Dán key (vd. `TCL1-XXXX-XXXX-XXXX`)
- **Kích hoạt key trên máy này**

Khi **Chạy**, tool heartbeat: gắn máy (nếu còn slot) và trừ record/ngày theo số từ khóa.

## API

- `POST /api/license/activate` `{ key, machine_id, hostname, os }`
- `POST /api/license/heartbeat` thêm `records_delta`
