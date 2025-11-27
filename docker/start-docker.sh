#!/bin/bash
# Script khởi động nhanh cho Docker Compose

set -e

echo "🚀 Cyber-Mentor AI - Docker Setup"
echo "=================================="

# Kiểm tra Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker chưa được cài đặt!"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose chưa được cài đặt!"
    exit 1
fi

# Kiểm tra .env file
if [ ! -f .env ]; then
    echo "⚠️  File .env không tồn tại!"
    echo "📝 Tạo file .env từ .env.example..."
    cp .env.example .env
    echo "✅ Đã tạo file .env"
    echo "⚠️  Vui lòng chỉnh sửa file .env và thêm GEMINI_API_KEY"
    echo "   Sau đó chạy lại script này."
    exit 1
fi

# Kiểm tra GEMINI_API_KEY
if grep -q "your_gemini_api_key_here" .env; then
    echo "⚠️  GEMINI_API_KEY chưa được cấu hình!"
    echo "   Vui lòng chỉnh sửa file .env và thêm API key thực."
    exit 1
fi

echo "✅ Kiểm tra môi trường hoàn tất"
echo ""

# Build images
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting containers..."
docker-compose up -d

echo ""
echo "⏳ Đợi containers khởi động..."
sleep 10

echo ""
echo "✅ Ứng dụng đã sẵn sàng!"
echo ""
echo "📊 Truy cập:"
echo "   - Web UI: http://localhost:8501"
echo "   - Kali API: http://localhost:5000"
echo ""
echo "📝 Xem logs:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 Dừng ứng dụng:"
echo "   docker-compose down"
