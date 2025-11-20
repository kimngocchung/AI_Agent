# File: core/tools/burpsuite_tool.py (Phiên bản SỬA LỖI INDEX)

import os
import requests
import time
import json 
from langchain_core.tools import tool
from dotenv import load_dotenv
from typing import List, Optional

# Tải biến môi trường
load_dotenv()

BURP_API_URL = os.getenv("BURP_API_URL")
BURP_API_KEY = os.getenv("BURP_API_KEY")

def _get_burp_api_headers():
    """Hàm helper để tạo headers xác thực."""
    if not BURP_API_KEY:
        raise ValueError("Lỗi: BURP_API_KEY không được tìm thấy trong file .env")
    return {
        "Authorization": f"Bearer {BURP_API_KEY}"
    }

@tool
def get_burp_request_by_index(request_index: int) -> str:
    """
    Lấy thông tin chi tiết của MỘT request/response duy nhất từ Burp Suite 
    HTTP history bằng CHỈ SỐ (#) của nó.
    
    Hãy dùng tool này khi người dùng yêu cầu phân tích một request cụ thể
    (ví dụ: "Phân tích request số 1", "Xem request 35").

    Args:
        request_index (int): 
            Chỉ số (số thứ tự #) của request mà người dùng thấy trên giao diện Burp.
            Lưu ý: Chỉ số này là 1-based (bắt đầu từ 1).

    Returns:
        str: Một chuỗi JSON chứa toàn bộ chi tiết request và response, 
             hoặc thông báo lỗi.
    """
    
    if not BURP_API_URL or not BURP_API_KEY:
        return "Lỗi: BURP_API_URL hoặc BURP_API_KEY chưa được cấu hình trong .env."

    print(f"--- [Tool: Burp] Đang lấy request theo CHỈ SỐ: {request_index} từ {BURP_API_URL} ---")
    
    try:
        api_endpoint = f"{BURP_API_URL}/v0.1/proxy/history"
        headers = _get_burp_api_headers()
        
        # Gọi API của Burp để LẤY TOÀN BỘ lịch sử
        response = requests.get(api_endpoint, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        all_requests = data.get("request_responses", [])
        
        if not all_requests:
            return "Burp Proxy history trống."

        # --- LOGIC SỬA LỖI (QUAN TRỌNG) ---
        # Chuyển đổi index 1-based (người dùng thấy) sang 0-based (list Python)
        target_index_0based = request_index - 1

        # Kiểm tra xem index có hợp lệ không
        if target_index_0based < 0 or target_index_0based >= len(all_requests):
            return f"Lỗi: Không tìm thấy request nào có chỉ số #{request_index}. Lịch sử chỉ có {len(all_requests)} request."

        # Lấy đúng request bằng CHỈ SỐ MẢNG
        # Burp trả về lịch sử MỚI NHẤT ở ĐẦU (index 0)
        # Giao diện Burp cũng hiển thị MỚI NHẤT ở ĐẦU (ID lớn nhất)
        # Chúng ta giả định thứ tự API trả về khớp với thứ tự GUI
        found_item = all_requests[target_index_0based]
        
        # Chuyển đổi dict Python thành chuỗi JSON cho AI "đọc"
        result_json = json.dumps(found_item, indent=2)

        print(f"--- [Tool: Burp] Đã tìm thấy và trả về request tại index: {target_index_0based} ---")
        
        time.sleep(1) 
        
        return result_json

    except requests.exceptions.ConnectionError:
        return f"Lỗi kết nối: Không thể kết nối đến Burp Suite API tại {BURP_API_URL}. Em đã bật API trên Burp Pro chưa?"
    except Exception as e:
        return f"Lỗi khi gọi Burp API: {str(e)}"