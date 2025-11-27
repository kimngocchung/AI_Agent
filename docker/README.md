# 🐳 Docker Version - Cyber-Mentor AI

Chạy toàn bộ ứng dụng trong Docker containers (không cần máy Kali riêng).

## 📦 Cấu Trúc

- `Dockerfile`: Streamlit App container
- `Dockerfile.kali`: Kali Linux container với pentest tools
- `docker-compose.yml`: Orchestration
- `start-docker.bat/sh`: Script tự động khởi động

## 🚀 Cách Sử Dụng

### Cách 1: Docker Compose (Khuyến nghị)

```bash
# Build và chạy
docker-compose up -d --build

# Xem logs
docker-compose logs -f

# Dừng
docker-compose down
```

### Cách 2: Script Tự Động

**Windows:**
```cmd
start-docker.bat
```

**Linux/Mac:**
```bash
chmod +x start-docker.sh
./start-docker.sh
```

### Cách 3: Manual (Không dùng docker-compose)

**Windows:**
```cmd
run-manual.bat
```

**Linux/Mac:**
```bash
chmod +x run-manual.sh
./run-manual.sh
```

## ⚙️ Cấu Hình

Tạo file `.env` trong folder gốc (không phải folder docker/):

```bash
GEMINI_API_KEY=your_api_key_here
```

## 📊 Truy Cập

- **Web UI**: http://localhost:8501
- **Kali API**: http://localhost:5000

## 🔧 Troubleshooting

### Build lâu / timeout

Nguyên nhân: Tải `torch` và `sentence-transformers` rất chậm.

Giải pháp:
- Đợi kiên nhẫn (có thể mất 10-20 phút)
- Hoặc dùng mirror:
  ```dockerfile
  RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ...
  ```

### Container không start

```bash
# Xem logs
docker-compose logs

# Rebuild từ đầu
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## 📖 Tài Liệu Chi Tiết

Xem file gốc `../README.md` để biết thêm về kiến trúc và cách sử dụng.
