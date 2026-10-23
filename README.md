# Void PTT Backend

FastAPI Backend được thiết kế theo chuẩn [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices), sử dụng **uv** (trình quản lý gói siêu tốc bằng Rust), kiến trúc Domain-Driven, và cấu hình tối ưu chi phí hạ tầng (Startup Production-ready).

---

## 📁 Cấu trúc Dự án (Domain-Driven Structure)

```text
void-ptt-backend/
├── alembic/                 # Async migrations (Alembic)
│   ├── versions/            # Thư mục chứa các file migration (đánh số theo ngày)
│   └── env.py               # Async migration runner kết nối SQLAlchemy Base
├── src/
│   ├── config.py            # AppSettings chung (môi trường, CORS, DB pool)
│   ├── database.py          # SQLAlchemy 2.0 AsyncEngine, async_sessionmaker, get_db
│   ├── models.py            # Base ORM (PostgreSQL naming conventions) & CustomModel (Pydantic)
│   ├── exceptions.py        # Global AppException hierarchy & exception handler
│   ├── pagination.py        # Module phân trang chuẩn (PaginationParams, PaginatedResponse)
│   ├── main.py              # FastAPI app, lifespan, CORS, health check, router registry
│   ├── auth/                # Domain Xác thực & Phân quyền
│   │   ├── config.py        # AuthConfig (JWT secret, thuật toán, thời gian hết hạn)
│   │   ├── constants.py     # TokenType, ErrorCode
│   │   ├── schemas.py       # Pydantic schemas (Login, Token, Refresh)
│   │   ├── service.py       # Password hash (pwdlib/Argon2), JWT encode/decode (PyJWT)
│   │   ├── dependencies.py  # get_current_user, get_current_active_user (Annotated)
│   │   ├── exceptions.py    # InvalidCredentials, TokenExpired, InvalidToken
│   │   └── router.py        # Endpoints: /auth/login, /auth/register, /auth/refresh, /auth/me
│   └── users/               # Domain Quản lý người dùng
│       ├── models.py        # User ORM model (UUID, email, hashed_password, timestamps)
│       ├── schemas.py       # UserCreate, UserRead, UserUpdate
│       ├── constants.py     # ErrorCode
│       ├── exceptions.py    # UserNotFound, EmailAlreadyExists, UserInactive
│       ├── service.py       # Business logic (SQL-first)
│       ├── dependencies.py  # valid_user_id (Dependency validation)
│       └── router.py        # CRUD /users endpoints với phân trang
├── tests/                   # Pytest Async tests (httpx ASGITransport)
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_health.py
├── .env.example             # Mẫu biến môi trường
├── alembic.ini              # Cấu hình migration
├── pyproject.toml           # Cấu hình uv, ruff, pytest
├── Dockerfile               # Multi-stage Dockerfile với uv (~120MB image)
├── docker-compose.yml       # Production stack: FastAPI + PostgreSQL + Caddy (Auto HTTPS)
├── Caddyfile                # Reverse proxy tự động cấp chứng chỉ SSL miễn phí
└── Makefile                 # Lệnh tắt tiện ích
```

---

## ⚡ Bắt đầu Nhanh với `uv`

### 1. Cài đặt dependencies

```bash
uv sync --all-groups
```

### 2. Chạy ứng dụng local

```bash
make dev
# Hoặc: uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger Docs (chỉ mở ở local/staging): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

### 3. Chạy tests & lint

```bash
make test    # Chạy pytest async test suite
make lint    # Kiểm tra & tự sửa lỗi với ruff
make format  # Định dạng code chuẩn ruff
```

---

## Kết nối với Supabase

Khi bạn tạo project trên **Supabase**:

1. Vào **Project Settings** → **Database** → **Connection string**.
2. Chọn tab **URI** (hoặc copy Connection parameters).
3. Đổi protocol thành `postgresql+asyncpg://` và dán vào file `.env`:

```env
# Định dạng chuẩn với Supabase Connection Pooling (Session mode - port 5432):
DATABASE_URL="postgresql+asyncpg://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres"
```

> **Lưu ý:**
>
> - `asyncpg` chạy tốt nhất với **Direct Connection** hoặc **Session Pooler** (port 5432).
> - Nếu dùng Transaction Pooler (port 6543), cần cấu hình thêm `statement_cache_size=0` trong asyncpg. Do đó dùng port 5432 của Supabase Pooler là tiện và chuẩn nhất.

Sau khi điền `.env`, chạy migration để tạo bảng trên Supabase:

```bash
make migrate
# Lệnh tương đương: uv run alembic upgrade head
```

---

## 💰 Chiến Lược Tiết Kiệm Chi Phí Nhất (Cho Startup)

1. **Database:** Dùng **Supabase Free Tier** (500MB DB, automated backup, web UI quản trị, $0/tháng).
2. **Compute:** Thuê 1 VPS giá rẻ (Hetzner €3.5/tháng hoặc DigitalOcean/Linode $4-$5/tháng) hoặc dùng Free Tier (Oracle Cloud VPS miễn phí 4 OCPU 24GB RAM).
3. **SSL & Reverse Proxy:** Dùng **Caddy** (có sẵn trong `docker-compose.yml` và `Caddyfile`). Caddy tự động lấy và gia hạn SSL Let's Encrypt hoàn toàn miễn phí, tiêu tốn chỉ ~15MB RAM so với cấu hình Nginx phức tạp.
4. **Memory Footprint:** Nhờ chạy async coroutines (FastAPI + asyncpg) và Docker image build từ `uv` (~120MB), toàn bộ backend hoạt động trơn tru chỉ với **< 150MB RAM**.
