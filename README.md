# 🏥 Hướng Dẫn Setup Chatbot Y Tế RAG System

## 📋 Yêu Cầu Hệ Thống

- UV
- Docker & Docker Compose

## 🚀 Hướng Dẫn Setup

### 1. Khởi động Docker PostgreSQL với pg-vector

```bash
docker compose -f compose.dev.yaml up
```

### 2. Cấu hình Database

#### 2.1. Kết nối Database với DBeaver (hoặc pgAdmin/psql)

**Thông tin kết nối:**

- Host: `localhost`
- Port: `5432`
- Database: `tailm`
- Username: `internet_crawler`
- Password: `123456`

**Với DBeaver:**

1. New Database Connection → PostgreSQL
2. Nhập thông tin connection ở trên
3. Test Connection → Finish

**Với psql command line:**

```bash
psql postgresql://internet_crawler:123456@localhost:5432/tailm
```

#### 2.2. Tạo Schema và Migration

```bash
UV_ENV_FILE=.env uv run alembic upgrade head
```

### 3. Setup Python Environment

```bash
uv sync --frozen
```

```bash
./scripts/dev.sh
```

### 4. Import Postman Collection

1. Mở Postman
2. Import file `postman_collection.json`
3. Set variable `base_url` = `http://localhost:8000`

## 📊 Architecture

```
Browser (chatbot.html)
    ↓ HTTP POST
FastAPI Server (server.py)
    ↓
ChatbotService (RAG Pipeline)
    ↓
PostgreSQL + pgvector (Vector Search)
    ↓
Gemini API (LLM Generation)
```

## 🚨 Troubleshooting

**Lỗi PostgreSQL Connection:**

```bash
# Kiểm tra Docker container
docker ps

# Restart PostgreSQL
docker compose -f compose.dev.yaml restart db

# Xem logs
docker compose -f compose.dev.yaml logs db
```

**Lỗi pgvector extension:**

```sql
-- Connect vào PostgreSQL và chạy
CREATE EXTENSION IF NOT EXISTS vector;
```

**Lỗi CORS:**

- Đảm bảo server chạy trên `localhost:8000`
- Kiểm tra CORS settings trong FastAPI
