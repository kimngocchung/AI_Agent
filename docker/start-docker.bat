@echo off
REM Script khởi động nhanh cho Docker Compose trên Windows

echo 🚀 Cyber-Mentor AI - Docker Setup
echo ==================================

REM Kiểm tra Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker chưa được cài đặt!
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker Compose chưa được cài đặt!
    pause
    exit /b 1
)

REM Kiểm tra .env file
if not exist .env (
    echo ⚠️  File .env không tồn tại!
    echo 📝 Tạo file .env từ .env.example...
    copy .env.example .env
    echo ✅ Đã tạo file .env
    echo ⚠️  Vui lòng chỉnh sửa file .env và thêm GEMINI_API_KEY
    echo    Sau đó chạy lại script này.
    pause
    exit /b 1
)

REM Kiểm tra GEMINI_API_KEY
findstr /C:"your_gemini_api_key_here" .env >nul
if not errorlevel 1 (
    echo ⚠️  GEMINI_API_KEY chưa được cấu hình!
    echo    Vui lòng chỉnh sửa file .env và thêm API key thực.
    pause
    exit /b 1
)

echo ✅ Kiểm tra môi trường hoàn tất
echo.

REM Build images
echo 🔨 Building Docker images...
docker-compose build

echo.
echo 🚀 Starting containers...
docker-compose up -d

echo.
echo ⏳ Đợi containers khởi động...
timeout /t 10 /nobreak >nul

echo.
echo ✅ Ứng dụng đã sẵn sàng!
echo.
echo 📊 Truy cập:
echo    - Web UI: http://localhost:8501
echo    - Kali API: http://localhost:5000
echo.
echo 📝 Xem logs:
echo    docker-compose logs -f
echo.
echo 🛑 Dừng ứng dụng:
echo    docker-compose down
echo.
pause
