import requests
import os
import json
from dotenv import load_dotenv

# Tải biến môi trường
load_dotenv()

API_URL = os.getenv("BURP_API_URL")
API_KEY = os.getenv("BURP_API_KEY")

if not API_URL or not API_KEY:
    print("--- LỖI CẤU HÌNH ---")
    print("Không tìm thấy BURP_API_URL hoặc BURP_API_KEY trong file .env")
    print("Hãy kiểm tra lại file .env của bạn.")
    exit()

# Xây dựng headers y hệt như tool
headers = {
    "Authorization": f"Bearer {API_KEY}"
}

api_endpoint = f"{API_URL}/v0.1/proxy/history"
print(f"--- [Test Burp] Đang gửi yêu cầu (GET) đến: {api_endpoint} ---")

try:
    response = requests.get(api_endpoint, headers=headers, timeout=10)
    
    print(f"--- [Test Burp] Đã nhận Status Code: {response.status_code} ---")
    
    # Kiểm tra các lỗi HTTP (401=Sai key, 404=Sai URL)
    response.raise_for_status() 

    # Nếu thành công (Code 200 OK)
    data = response.json()
    all_requests = data.get("request_responses", [])
    
    print("\n--- THÀNH CÔNG! KẾT NỐI BURP API HOÀN HẢO! ---")
    print(f"Tìm thấy tổng cộng {len(all_requests)} request trong lịch sử Burp.")
    
    if all_requests:
        print("--- Dữ liệu của Request đầu tiên (index 0) ---")
        print(json.dumps(all_requests[0], indent=2))
    else:
        print("--- Lịch sử Burp đang trống. Hãy duyệt web để tạo request. ---")


except requests.exceptions.ConnectionError:
    print("\n--- LỖI KẾT NỐI (ConnectionError) ---")
    print(f"Không thể kết nối đến {API_URL}.")
    print("HÃY KIỂM TRA:")
    print("1. Đảm bảo Burp Suite Pro đang CHẠY.")
    print("2. Đảm bảo API đã được ENABLE trong Settings -> Burp Suite API.")
    print("3. Đảm bảo BURP_API_URL trong .env là chính xác (ví dụ: http://127.0.0.1:1337).")

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        print("\n--- LỖI XÁC THỰC (401 Unauthorized) ---")
        print("BURP_API_KEY trong file .env của bạn bị SAI.")
        print("Hãy vào Burp -> Settings -> API -> Bấm 'New' để tạo 1 key mới và dán lại vào .env.")
    elif e.response.status_code == 404:
        print("\n--- LỖI ĐƯỜNG DẪN (404 Not Found) ---")
        print(f"Endpoint {api_endpoint} không được tìm thấy.")
        print("HÃY KIỂM TRA: Đảm bảo BURP_API_URL trong .env là chính xác (không có dấu / thừa, đúng cổng).")
    else:
        print(f"\n--- LỖI HTTP KHÁC ({e.response.status_code}) ---")
        print(e)
        
except Exception as e:
    print(f"--- LỖI KHÔNG XÁC ĐỊNH ---")
    print(e)