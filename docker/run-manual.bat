@echo off
REM Script chạy Docker thủ công (không dùng docker-compose)

echo 🚀 Cyber-Mentor AI - Manual Docker Run
echo =====================================

REM 1. Tạo Docker Network (để 2 container nhìn thấy nhau)
echo 🌐 Creating Docker Network...
docker network create cyber-mentor-net 2>nul

REM 2. Build Images (nếu chưa có)
echo 🔨 Building Kali Image...
docker build -t cyber-mentor-kali -f Dockerfile.kali .

echo 🔨 Building App Image...
docker build -t cyber-mentor-app -f Dockerfile .

REM 3. Chạy Kali Container
echo 🚀 Starting Kali Container...
REM Xóa container cũ nếu có
docker rm -f cyber-mentor-kali 2>nul
REM Chạy container mới
docker run -d ^
  --name cyber-mentor-kali ^
  --network cyber-mentor-net ^
  -p 5000:5000 ^
  cyber-mentor-kali

REM 4. Chạy App Container
echo 🚀 Starting App Container...
REM Xóa container cũ nếu có
docker rm -f cyber-mentor-app 2>nul

REM Đọc API Key từ .env (cách đơn giản)
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="GEMINI_API_KEY" set GEMINI_API_KEY=%%b
)

REM Chạy container mới
docker run -d ^
  --name cyber-mentor-app ^
  --network cyber-mentor-net ^
  -p 8501:8501 ^
  -e GEMINI_API_KEY=%GEMINI_API_KEY% ^
  -e KALI_LISTENER_URL=http://cyber-mentor-kali:5000 ^
  -v "%cd%/chat_history.json:/app/data/chat_history.json" ^
  -v "%cd%/my_faiss_index:/app/my_faiss_index" ^
  cyber-mentor-app

echo.
echo ✅ Xong!
echo 📊 Web UI: http://localhost:8501
echo 📊 Kali API: http://localhost:5000
echo.
echo 📝 Xem logs:
echo    docker logs -f cyber-mentor-app
echo.
pause
