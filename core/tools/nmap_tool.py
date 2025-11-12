# File: core/tools/nmap_tool.py

import os
import requests
from langchain_core.tools import tool
from dotenv import load_dotenv

# Tải biến môi trường (để lấy KALI_LISTENER_URL)
load_dotenv()

# Lấy IP của máy KALI từ file .env
# Nếu không tìm thấy, dùng một IP placeholder (hãy đảm bảo bạn đã đặt nó trong .env)
KALI_LISTENER_URL = os.getenv("KALI_LISTENER_URL", "http://192.168.1.100:5000") 

@tool
def run_nmap_scan(target: str, scan_type: str = "basic") -> str:
    """
    Gửi yêu cầu quét Nmap đến máy Kali Listener một cách an toàn.
    AI Agent chỉ cần cung cấp 'target' (mục tiêu) và 'scan_type'.

    Args:
        target (str): IP hoặc domain cần quét.
        scan_type (str, optional): Loại quét. AI nên chọn một trong các loại sau:
            - 'basic': Quét nhanh (-sV, 1000 cổng TCP phổ biến nhất). Đây là mặc định.
            - 'full': Quét toàn diện tất cả 65535 cổng (-p-, -sV, -sC, -O).
            - 'vuln': Quét các script lỗ hổng cơ bản (--script vuln).
            
    Returns:
        str: Kết quả output thô từ Nmap, hoặc thông báo lỗi.
    """
    
    print(f"--- [Tool: Nmap] Nhận lệnh quét '{scan_type}' trên target: {target} ---")
    print(f"--- [Tool: Nmap] Đang gửi yêu cầu đến 'Tay' tại: {KALI_LISTENER_URL} ---")

    # Xây dựng các tham số (params) dựa trên scan_type
    if scan_type == "full":
        params = ["-p-", "-sV", "-sC", "-O", target]
    elif scan_type == "vuln":
        params = ["-sV", "--script", "vuln", target]
    else: # basic (mặc định)
        params = ["-sV", "-p", "1-1000", target]

    # Dữ liệu để gửi
    payload = {
        "tool": "nmap",
        "params": params
    }
    
    api_endpoint = f"{KALI_LISTENER_URL}/execute"

    try:
        # Gửi request POST đến máy Kali, timeout 610 giây (lớn hơn 10 phút của Kali)
        response = requests.post(api_endpoint, json=payload, timeout=610) 
        
        # Báo lỗi nếu HTTP status không phải 2xx (ví dụ: 403, 500)
        response.raise_for_status() 

        data = response.json()
        
        # Kiểm tra xem 'Tay' (Flask) có báo thành công không
        if data.get("success"):
            print("--- [Tool: Nmap] 'Tay' đã thực thi thành công. ---")
            return f"Kết quả quét Nmap từ Kali:\n{data.get('output')}"
        else:
            # Lỗi do chính tool Nmap báo về (ví dụ: không tìm thấy host)
            print(f"--- [Tool: Nmap] 'Tay' báo lỗi khi chạy tool: {data.get('error_output')} ---")
            return f"Máy Kali báo lỗi khi chạy Nmap: {data.get('error_output')}\nKết quả (nếu có): {data.get('output')}"

    except requests.exceptions.Timeout:
        print("--- [Tool: Nmap] Lỗi: Yêu cầu bị Timeout ---")
        return f"Lỗi: Yêu cầu đến Kali Listener bị timeout (quá 610 giây)."
    except requests.exceptions.ConnectionError:
        print("--- [Tool: Nmap] Lỗi: Không kết nối được 'Tay' ---")
        return f"Lỗi kết nối: Không thể kết nối đến Kali Listener tại {api_endpoint}. Hãy kiểm tra IP trong .env và đảm bảo Listener (kali_listener.py) đang chạy."
    except requests.exceptions.RequestException as e:
        # Các lỗi HTTP khác (403 Forbidden, 500 Internal Server Error từ Flask,...)
        print(f"--- [Tool: Nmap] Lỗi API: {e} ---")
        return f"Lỗi API: {str(e)}\nPhản hồi từ server: {e.response.text if e.response else 'Không có phản hồi'}"
    except Exception as e:
        # Các lỗi khác (ví dụ: lỗi JSON decode)
        print(f"--- [Tool: Nmap] Lỗi không xác định: {e} ---")
        return f"Lỗi không xác định khi gọi tool Nmap: {str(e)}"