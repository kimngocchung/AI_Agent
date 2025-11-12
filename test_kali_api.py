import requests
import os
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

KALI_URL = os.getenv("KALI_LISTENER_URL")

if not KALI_URL:
    print("LỖI: Không tìm thấy KALI_LISTENER_URL trong file .env")
    exit()

api_endpoint = f"{KALI_URL}/execute"
print(f"--- [Test Não] Đang gửi yêu cầu đến: {api_endpoint} ---")

# Xây dựng payload để test Nmap
nmap_payload = {
    "tool": "nmap",
    "params": ["-sV", "-p", "80,443", "scanme.nmap.org"] # Dùng target hợp pháp
}

try:
    response = requests.post(api_endpoint, json=nmap_payload, timeout=300)
    response.raise_for_status() # Báo lỗi nếu status code là 4xx/5xx

    print("--- [Test Não] Đã nhận phản hồi từ Kali ---")
    data = response.json()

    if data.get("success"):
        print("--- THÀNH CÔNG! ---")
        print("Kết quả Nmap từ Kali:")
        print(data.get("output"))
    else:
        print("--- LỖI TỪ KALI ---")
        print(data.get("error_output"))

except requests.exceptions.ConnectionError:
    print(f"LỖI KẾT NỐI: Không thể kết nối đến {api_endpoint}.")
    print("Hãy kiểm tra lại IP trong .env và đảm bảo Kali Listener đang chạy.")
except requests.exceptions.Timeout:
    print("LỖI TIMEOUT: Yêu cầu bị hết hạn. Kiểm tra mạng hoặc tool chạy quá lâu.")
except Exception as e:
    print(f"LỖI KHÔNG XÁC ĐỊNH: {e}")