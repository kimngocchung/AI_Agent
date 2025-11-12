# File: core/tools/dirsearch_tool.py

from langchain_core.tools import tool
import requests
import os

KALI_LISTENER_URL = os.getenv("KALI_LISTENER_URL")

@tool
def run_dirsearch_scan(url: str, params: str = "-e php,html,js") -> str:
    """Gửi yêu cầu quét Dirsearch đến máy Kali Listener."""
    print(f"--- [Agent] Gửi yêu cầu Dirsearch đến Kali: {url} ---")

    param_list = params.split()
    param_list.extend(["-u", url])

    payload = {
        "tool": "dirsearch",
        "params": param_list
    }

    if not KALI_LISTENER_URL:
        return "Lỗi: Biến môi trường KALI_LISTENER_URL chưa được cài đặt."

    try:
        response = requests.post(f"{KALI_LISTENER_URL}/execute", json=payload, timeout=610)
        response.raise_for_status()

        data = response.json()
        if data.get("success"):
            return f"Kết quả quét Dirsearch từ Kali:\n{data.get('output')}"
        else:
            return f"Máy Kali báo lỗi khi chạy Dirsearch: {data.get('error_output')}"

    except requests.exceptions.RequestException as e:
        return f"Lỗi kết nối đến máy Kali Listener: {str(e)}"
    except Exception as e:
        return f"Lỗi không xác định: {str(e)}"
