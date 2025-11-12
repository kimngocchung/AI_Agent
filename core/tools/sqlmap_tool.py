# File: core/tools/sqlmap_tool.py (Phiên bản "Làm mát" API)

import os
import requests
import time  # <<< 1. THÊM IMPORT NÀY
from langchain_core.tools import tool
from dotenv import load_dotenv
from typing import List, Optional

# Tải biến môi trường (để lấy KALI_LISTENER_URL)
load_dotenv()

# Lấy IP của máy KALI từ file .env
KALI_LISTENER_URL = os.getenv("KALI_LISTENER_URL", "http://192.168.1.100:5000") 

@tool
def run_sqlmap_scan(url: str, params: Optional[List[str]] = None) -> str:
    """
    Gửi yêu cầu quét SQLMap đến máy Kali Listener một cách an toàn.
    Công cụ sẽ TỰ ĐỘNG thêm cờ '--batch' để chạy không tương tác.

    Args:
        url (str): URL mục tiêu (phải bao gồm cả tham số, 
                     ví dụ: "http://testphp.vulnweb.com/listproducts.php?cat=1").
        params (Optional[List[str]], optional): Một danh sách các cờ (flags) bổ sung
            để truyền cho SQLMap.
            Ví dụ: ["--dbs"] hoặc ["--tables", "-D", "dbname"]
            Nếu không cung cấp, AI sẽ mặc định chạy kiểm tra cơ bản.

    Returns:
        str: Kết quả output thô từ SQLMap, hoặc thông báo lỗi.
    """
    
    print(f"--- [Tool: SQLMap] Nhận lệnh quét trên URL: {url} ---")
    print(f"--- [Tool: SQLMap] Đang gửi yêu cầu đến 'Pentest Tools' tại: {KALI_LISTENER_URL} ---")
    
    # Xây dựng các tham số (params)
    # Bắt đầu với lệnh cơ bản
    final_params = ["-u", url]
    
    # Thêm các tham số bổ sung nếu AI cung cấp
    if params:
        final_params.extend(params)
        
    # LUÔN LUÔN thêm "--batch" để đảm bảo tool chạy tự động, không bị treo
    if "--batch" not in final_params:
        final_params.append("--batch")

    # Dữ liệu để gửi
    payload = {
        "tool": "sqlmap",
        "params": final_params
    }
    
    api_endpoint = f"{KALI_LISTENER_URL}/execute"

    try:
        # Gửi request POST đến máy Kali, timeout 610 giây
        response = requests.post(api_endpoint, json=payload, timeout=610) 
        response.raise_for_status() # Báo lỗi nếu HTTP status không phải 2xx

        data = response.json()
        
        if data.get("success"):
            print("--- [Tool: SQLMap] 'Pentest Tools' đã thực thi thành công. ---")
            
            # <<< 2. THÊM DÒNG NÀY ĐỂ "LÀM MÁT" API TRƯỚC KHI TRẢ VỀ >>>
            print("--- [Tool: SQLMap] Đang chờ 4 giây để tránh lỗi 429... ---")
            time.sleep(4) 
            
            return f"Kết quả quét SQLMap từ Kali:\n{data.get('output')}"
        else:
            # Lỗi do chính tool SQLMap báo về
            print(f"--- [Tool: SQLMap] 'Pentest Tools' báo lỗi khi chạy tool: {data.get('error_output')} ---")
            return f"Máy Kali báo lỗi khi chạy SQLMap: {data.get('error_output')}\nKết quả (nếu có): {data.get('output')}"

    except requests.exceptions.Timeout:
        print("--- [Tool: SQLMap] Lỗi: Yêu cầu bị Timeout ---")
        return f"Lỗi: Yêu cầu đến Kali Listener bị timeout (quá 610 giây)."
    except requests.exceptions.ConnectionError:
        print("--- [Tool: SQLMap] Lỗi: Không kết nối được 'Kali linux' ---")
        return f"Lỗi kết nối: Không thể kết nối đến Kali Listener tại {api_endpoint}. Hãy kiểm tra IP trong .env và đảm bảo Listener (kali_listener.py) đang chạy."
    except requests.exceptions.RequestException as e:
        # Các lỗi HTTP khác
        print(f"--- [Tool: SQLMap] Lỗi API: {e} ---")
        return f"Lỗi API: {str(e)}\nPhản hồi từ server: {e.response.text if e.response else 'Không có phản hồi'}"
    except Exception as e:
        # Các lỗi khác
        print(f"--- [Tool: SQLMap] Lỗi không xác định: {e} ---")
        return f"Lỗi không xác định khi gọi tool SQLMap: {str(e)}"