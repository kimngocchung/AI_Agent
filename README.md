# 🚀 Cyber-Mentor AI - AI Pentesting Assistant

AI-powered Penetration Testing Assistant sử dụng Google Gemini AI, LangChain và RAG (FAISS Vector Store).

## ✨ Tính Năng

- 🤖 **3 Luồng Xử lý Thông minh**:
  - RAG Direct: Hỏi đáp lý thuyết về lỗ hổng bảo mật
  - Full Plan Chain: Lập kế hoạch pentest chi tiết (4 bước)
  - Agent Executor: Thực thi công cụ pentest (Nmap, SQLMap)

- 💬 **Multi-Chat Management**: Quản lý nhiều cuộc trò chuyện
- 🗑️ **Delete Conversations**: Xóa cuộc trò chuyện không cần thiết
- 💾 **Persistent Storage**: Lịch sử chat được lưu tự động vào `chat_history.json`
- 🔄 **Human-in-the-Loop**: Người dùng phê duyệt trước khi thực thi lệnh
- 📚 **RAG System**: Vector search với FAISS

## 📋 Yêu Cầu

- Python 3.11+
- Máy Kali Linux riêng (để chạy pentest tools)
- Gemini API Key

## 🚀 Cài Đặt

### 1. Clone Repository

```bash
git clone <your-repo>
cd AI_Agent
```

### 2. Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu Hình Environment

Tạo file `.env`:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
KALI_LISTENER_URL=http://192.168.1.100:5000
```

### 4. Chạy Kali Listener (trên máy Kali Linux)

```bash
python3 kali_listener.py
# Server sẽ chạy tại http://0.0.0.0:5000
```

### 5. Chạy Streamlit App (trên máy chính)

```bash
streamlit run app.py
```

Truy cập: http://localhost:8501

## 🐳 Docker Version

Nếu muốn chạy toàn bộ trong Docker (không cần máy Kali riêng), xem hướng dẫn trong folder `docker/`:

```bash
cd docker
./start-docker.bat  # Windows
./start-docker.sh   # Linux/Mac
```

## 📁 Cấu Trúc Dự Án

```
AI_Agent/
├── app.py                      # Streamlit Web UI
├── main.py                     # CLI Interface
├── kali_listener.py            # Flask API (chạy trên Kali)
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables
├── chat_history.json           # Persistent chat storage
│
├── core/                       # Core Logic
│   ├── router.py              # Router - Phân loại 3 luồng
│   ├── agents/                # Agent Executors
│   ├── chains/                # LangChain Chains
│   └── tools/                 # Pentest Tools
│
├── my_faiss_index/            # RAG Vector Database
└── docker/                    # Docker setup (optional)
```

## 🎯 Cách Sử Dụng

### **Web UI (Streamlit)**

1. Mở http://localhost:8501
2. Nhập yêu cầu (ví dụ: "Quét Nmap scanme.nmap.org")
3. AI sẽ phân tích và đề xuất
4. Click "Chấp nhận" để thực thi

### **CLI (Terminal)**

```bash
python main.py
```

## 🔧 Các Lệnh Hữu Ích

```bash
# Test kết nối với Kali
python test_kali_api.py

# Chạy Web UI
streamlit run app.py

# Chạy CLI
python main.py
```

## �️ Tính Năng Mới

### **v2.0** (Current)
- ✅ Nút xóa cuộc trò chuyện
- ✅ Lưu trữ persistent (chat_history.json)
- ✅ Multi-conversation management
- ✅ Tự động lưu khi có thay đổi

## 🔐 Bảo Mật

- ⚠️ Chỉ chạy trong mạng nội bộ
- ⚠️ Không expose Kali Listener ra internet
- ✅ Sử dụng firewall để giới hạn truy cập

## � License

MIT License

## 🙏 Credits

- **LangChain**: AI Framework
- **Google Gemini**: LLM API
- **Kali Linux**: Pentest Tools
- **Streamlit**: Web UI Framework
