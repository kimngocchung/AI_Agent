#!/bin/bash
# Script chạy Docker thủ công (không dùng docker-compose)

echo "🚀 Cyber-Mentor AI - Manual Docker Run"
echo "====================================="

# 1. Tạo Docker Network
echo "🌐 Creating Docker Network..."
docker network create cyber-mentor-net 2>/dev/null || true

# 2. Build Images
echo "🔨 Building Kali Image..."
docker build -t cyber-mentor-kali -f Dockerfile.kali .

echo "🔨 Building App Image..."
docker build -t cyber-mentor-app -f Dockerfile .

# 3. Chạy Kali Container
echo "🚀 Starting Kali Container..."
docker rm -f cyber-mentor-kali 2>/dev/null
docker run -d \
  --name cyber-mentor-kali \
  --network cyber-mentor-net \
  -p 5000:5000 \
  cyber-mentor-kali

# 4. Chạy App Container
echo "🚀 Starting App Container..."
docker rm -f cyber-mentor-app 2>/dev/null

# Load .env
if [ -f .env ]; then
  export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

docker run -d \
  --name cyber-mentor-app \
  --network cyber-mentor-net \
  -p 8501:8501 \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  -e KALI_LISTENER_URL=http://cyber-mentor-kali:5000 \
  -v "$(pwd)/chat_history.json:/app/data/chat_history.json" \
  -v "$(pwd)/my_faiss_index:/app/my_faiss_index" \
  cyber-mentor-app

echo ""
echo "✅ Xong!"
echo "📊 Web UI: http://localhost:8501"
echo "📊 Kali API: http://localhost:5000"
echo ""
echo "📝 Xem logs:"
echo "   docker logs -f cyber-mentor-app"
