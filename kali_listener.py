from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

# Chỉ định rõ các công cụ được phép chạy
ALLOWED_TOOLS = {
    "nmap": "/usr/bin/nmap",
    "sqlmap": "/usr/bin/sqlmap", # Cần kiểm tra đường dẫn
    "dirsearch": "/usr/bin/dirsearch" # Cần kiểm tra đường dẫn
}

@app.route("/execute", methods=["POST"])
def execute_command():
    data = request.json
    tool = data.get("tool")
    params = data.get("params") # params là một danh sách, ví dụ: ["-sV", "target.com"]

    if not tool or not params:
        return jsonify({"error": "Thiếu 'tool' hoặc 'params'"}), 400

    if tool not in ALLOWED_TOOLS:
        return jsonify({"error": f"Công cụ '{tool}' không được phép"}), 403

    # Xây dựng lệnh an toàn (tránh command injection)
    command = [ALLOWED_TOOLS[tool]] + params

    try:
        print(f"--- [Kali Listener] Đang chạy lệnh: {' '.join(command)} ---")
        # Chạy lệnh
        result = subprocess.run(command, capture_output=True, text=True, timeout=600, check=True)

        # Trả về kết quả thành công
        return jsonify({
            "success": True,
            "tool": tool,
            "output": result.stdout,
            "error_output": result.stderr
        })

    except subprocess.CalledProcessError as e:
        # Trả về lỗi nếu lệnh thất bại
         return jsonify({
            "success": False,
            "tool": tool,
            "output": e.stdout,
            "error_output": e.stderr
        }), 500
    except Exception as e:
        return jsonify({"error": f"Lỗi server nội bộ: {str(e)}"}), 500

if __name__ == '__main__':
    # Chạy server trên tất cả các IP của máy Kali, port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
