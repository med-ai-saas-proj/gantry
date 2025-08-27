# 🏥 Hướng Dẫn Setup Chatbot Y Tế RAG System

## 📋 Yêu Cầu Hệ Thống

- Python 3.12
- Docker & Docker Compose
- PostgreSQL với pg-vector extension

## 🚀 Hướng Dẫn Setup

### 1. Khởi động Docker PostgreSQL với pg-vector

```bash
docker run -d \
  --name postgres-pgvector \
  -e POSTGRES_DB=tailm \
  -e POSTGRES_USER=internet_crawler \
  -e POSTGRES_PASSWORD=123456 \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  --restart unless-stopped \
  pgvector/pgvector:pg16
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
psql postgres://internet_crawler:123456@localhost:5432/tailm
```

#### 2.2. Tạo Schema và Migration

**Bước 1: Tạo schema `tailm`**

```sql
CREATE SCHEMA IF NOT EXISTS "tailm";
```

**Bước 2: Enable pgvector extension**

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**Bước 3: Run migration scripts**

Chạy các file SQL trong thư mục `migrations/` theo thứ tự:

1. `migrations/001_create_tables.sql`
2. `migrations/002_add_indexes.sql`
3. (các file migration khác nếu có)

Hoặc chạy từng script:

```bash
# Với psql
psql postgres://internet_crawler:123456@localhost:5432/tailm -f migrations/001_create_tables.sql
psql postgres://internet_crawler:123456@localhost:5432/tailm -f migrations/002_add_indexes.sql

# Hoặc copy-paste nội dung từng file vào DBeaver và execute
```

### 3. Setup Python Environment

```bash
# Tạo virtual environment
python3.12 -m venv venv

# Activate virtual environment
source ./venv/bin/activate

# Install dependencies
pip install -r requirements.prod.txt
```

### 3. Khởi Động Server

```bash
python server.py
```

### 4. Import Postman Collection

1. Mở Postman
2. Import file `postman_collection.json`
3. Set variable `base_url` = `http://localhost:8000`

### 5. Upload Regulation Sample

Sử dụng API **POST /regulations/regulations** với JSON payload:

```json
{
  "title": "Quy định tiếp nhận, quản lý, chăm sóc, nuôi dưỡng, điều trị và phục hồi chức năng cho đối tượng tâm thần của Trung tâm Chăm sóc và Phục hồi chức năng người tâm thần số 1 Hà Nội",
  "content": "# SỞ Y TẾ HÀ NỘI\n## TRUNG TÂM CHĂM SÓC VÀ PHỤC HỒI CHỨC NĂNG NGƯỜI TÂM THẦN SỐ 1\n\n### CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n*Độc lập - Tự do - Hạnh phúc*\n\n# QUY ĐỊNH\n**Tiếp nhận, quản lý, chăm sóc, nuôi dưỡng, điều trị và phục hồi chức năng cho đối tượng tâm thần của Trung tâm Chăm sóc và Phục hồi chức năng người tâm thần số 1 Hà Nội**\n\n## Chương I - NHỮNG QUY ĐỊNH CHUNG\n\n### Điều 1. Mục đích, yêu cầu:\n1. Nhằm nâng cao chất lượng công tác tiếp nhận, bàn giao và tổ chức thăm gặp cho đối tượng tâm thần, hướng tới xây dựng môi trường làm việc văn minh, chuyên nghiệp và thân thiện\n2. Cụ thể hóa các quy trình về công tác tiếp nhận, bàn giao và tổ chức thăm gặp đối tượng\n3. Bảo đảm quyền được chăm sóc, phục hồi chức năng cho các đối tượng tự nguyện\n4. Đảm bảo tính công khai, minh bạch trong thực hiện nhiệm vụ chuyên môn\n\n### Điều 2. Phạm vi, đối tượng:\n- **Phạm vi**: Quy chế áp dụng thực hiện giải quyết các quy trình thủ tục hành chính cho đối tượng tâm thần tại Trung tâm\n- **Đối tượng**: Viên chức, lao động hợp đồng, các tổ chức, cá nhân có liên quan\n\n## Chương II - QUY ĐỊNH TIẾP NHẬN ĐỐI TƯỢNG HƯỞNG NGÂN SÁCH NHÀ NƯỚC\n\n### Điều 3. Điều kiện tiếp nhận đối tượng vào Trung tâm:\n- Người khuyết tật dạng thần kinh, tâm thần đặc biệt nặng, có hoàn cảnh khó khăn, không nơi nương tựa\n- Người khuyết tật dạng thần kinh, tâm thần nặng thuộc hộ nghèo/hộ cận nghèo\n\n### Điều 4. Trình tự thủ tục tiếp nhận:\n\n#### 1. Hồ sơ tiếp nhận đối tượng:\n**1.1. Đối tượng từ xã/phường chuyển đến:**\n- Quyết định tiếp nhận của Giám đốc Trung tâm\n- Ảnh 4x6 (5 cái)\n- Thẻ bảo hiểm y tế (nếu có)\n- Giấy tờ khác liên quan (Bản sao công chứng CCCD)\n\n**1.2. Đối tượng tâm thần lang thang từ Bệnh viện Tâm thần:**\n- Quyết định tiếp nhận của Giám đốc Trung tâm\n- Quyết định tiếp nhận đối tượng bảo trợ vào Trung tâm\n\n#### 2. Trình tự thủ tục tiếp nhận:\n**2.1. Từ xã/phường:**\n- **Bước 1**: Tư vấn thủ tục gia đình (30 ngày làm việc)\n- **Bước 2**: Kiểm tra hồ sơ, tiếp nhận đối tượng và kiểm tra sức khỏe ban đầu\n- **Bước 3**: Khám sàng lọc và lập kế hoạch trợ giúp (tối thiểu 7 ngày)\n- **Bước 4**: Tư vấn quy trình thăm gặp và phổ biến nội quy\n- **Bước 5**: Hoàn thiện hồ sơ quản lý đối tượng\n\n**2.2. Từ Bệnh viện Tâm thần/Trung tâm BTXH:**\n- **Bước 1**: Tiếp nhận đối tượng và kiểm tra hồ sơ\n- **Bước 2**: Phối hợp tiếp nhận và kiểm tra sức khỏe\n- **Bước 3**: Khám sàng lọc và lập kế hoạch trợ giúp\n- **Bước 4**: Hoàn thiện hồ sơ quản lý đối tượng\n\n## Chương III - QUY TRÌNH GIẢI QUYẾT CHO ĐỐI TƯỢNG VỀ THĂM GIA ĐÌNH\n\n### Điều 5. Hồ sơ thủ tục:\n- Mỗi đối tượng được giải quyết **tối đa 03 lần/1 năm** về thăm gia đình\n- Mỗi lần giải quyết **không quá 15 ngày** (trường hợp đặc biệt tối đa 30 ngày)\n- **Hồ sơ gồm**: Đơn đề nghị của người giám hộ, Bản sao CCCD người đón\n\n### Điều 6. Trình tự giải quyết:\n\n#### 1. Tại Trung tâm:\n- **Bước 1**: Đăng ký trước ít nhất **02 ngày** qua Zalo, Facebook, website, hotline\n- **Bước 2**: Kiểm tra hồ sơ giấy tờ\n- **Bước 3**: Phối hợp kiểm tra sức khỏe cho đối tượng\n- **Bước 4**: Ban hành Quyết định và lập biên bản bàn giao\n- **Bước 5**: Thực hiện kiểm tra, bàn giao tại cổng Trung tâm\n\n#### 2. Tại Bệnh viện (hết đợt điều trị):\n- **Bước 1**: Gia đình đề nghị về thăm gia đình tại viện\n- **Bước 2**: Chuẩn bị hồ sơ bàn giao\n- **Bước 3**: Chuẩn bị thuốc và thực hiện bàn giao tại viện\n- **Bước 4**: Bàn giao hồ sơ lưu trữ tại Trung tâm\n\n#### 3. Gia hạn thời gian về thăm gia đình:\n- **Bước 1**: Đăng ký gia hạn trước **03 ngày**\n- **Bước 2**: Tiếp nhận thông tin và báo cáo lãnh đạo\n- **Bước 3**: Thông báo kết quả cho gia đình\n- **Bước 4**: Thực hiện thủ tục gia hạn tại Trung tâm\n- **Bước 5**: Lưu hồ sơ\n\n### Điều 7. Tiếp nhận đối tượng trở lại:\n- **Bước 1**: Tiếp đón gia đình đối tượng\n- **Bước 2**: Phối hợp kiểm tra sức khỏe cho đối tượng\n- **Bước 3**: Thực hiện bàn giao và hoàn thiện hồ sơ tiếp nhận\n\n## Chương IV - QUY ĐỊNH DỪNG TRỢ GIÚP XÃ HỘI\n\n### Điều 8. Điều kiện dừng trợ giúp xã hội:\n- Đối tượng đủ điều kiện dừng trợ giúp theo quyết định Giám đốc Trung tâm\n- Đối tượng/người giám hộ, gia đình có đơn đề nghị xin dừng trợ giúp\n- Đối tượng không trở lại Trung tâm sau **30 ngày** kể từ ngày hết hạn về thăm gia đình\n- Đối tượng chết hoặc mất tích theo quy định pháp luật\n- Đối tượng lang thang đã xác định được gia đình nhưng chưa đủ điều kiện\n\n### Điều 9. Trình tự dừng trợ giúp xã hội:\n- **Bước 1**: Lập danh sách đối tượng đủ điều kiện theo định kỳ\n- **Bước 2**: Hội đồng xét duyệt đánh giá đối tượng\n- **Bước 3**: Giám đốc ra Quyết định dừng trợ giúp xã hội\n- **Bước 4**: Bàn giao đối tượng về cộng đồng\n- **Bước 5**: Báo cáo Sở Y tế"
}
```

### 6. Mở Chatbot Interface

```bash
# Mở file trong browser
open chatbot.html
# hoặc
firefox chatbot.html
# hoặc đường dẫn: file:///path/to/ragTailm/chatbot.html
```

## 🧪 Test Chatbot

Thử các câu hỏi mẫu:

- "Trung tâm tiếp nhận những đối tượng tâm thần nào vào điều trị và chăm sóc?"
- "Điều kiện cần thiết để được tiếp nhận vào Trung tâm là gì?"
- "Thủ tục về thăm gia đình như thế nào?"
- "Quy trình dừng trợ giúp xã hội ra sao?"

## 🔧 Cấu Hình Database Connection

Connection string mặc định:

```
postgres://internet_crawler:123456@localhost:5432/tailm
```

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
docker restart postgres-pgvector

# Xem logs
docker logs postgres-pgvector
```

**Lỗi pgvector extension:**

```sql
-- Connect vào PostgreSQL và chạy
CREATE EXTENSION IF NOT EXISTS vector;
```

**Lỗi CORS:**

- Đảm bảo server chạy trên `localhost:8000`
- Kiểm tra CORS settings trong FastAPI
