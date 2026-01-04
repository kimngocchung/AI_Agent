"""
Local Script Runner Tool

Chạy script ngay trên máy hiện tại (Python hoặc Bash), trả về stdout/stderr/return_code
để Agent phân tích và thử lại nếu cần. Dùng cho trường hợp không muốn/không thể
gửi sang Kali listener.
"""

import subprocess
import tempfile
import os
import shlex
from typing import Optional
from langchain_core.tools import tool


@tool
def run_local_script(
    script_content: str,
    script_type: str = "python",
    args: str = "",
    timeout: int = 180
) -> str:
    """
    Chạy script cục bộ (python/bash) và trả về log chi tiết.

    Args:
        script_content: Nội dung script.
        script_type: "python" hoặc "bash".
        args: Tham số dòng lệnh (chuỗi).
        timeout: Giới hạn thời gian (giây).

    Returns:
        Chuỗi markdown chứa stdout/stderr/return_code và gợi ý tiếp theo.
    """
    if not script_content:
        return "❌ Thiếu script_content."

    script_type = script_type.lower()
    if script_type not in ("python", "bash"):
        return "❌ script_type phải là 'python' hoặc 'bash'."

    suffix = ".py" if script_type == "python" else ".sh"
    interpreter = "python" if script_type == "python" else "bash"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as tmp:
            tmp.write(script_content)
            tmp_path = tmp.name

        if script_type == "bash":
            os.chmod(tmp_path, 0o755)

        cmd = [interpreter, tmp_path]
        if args:
            cmd.extend(shlex.split(args))

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        rc = proc.returncode

        note = []
        if not stdout and not stderr:
            note.append("⚠️ stdout/stderr trống - kiểm tra logic script hoặc thêm --verbose/print.")
        if rc != 0:
            note.append(f"⚠️ return_code={rc} (có thể do lỗi parser/logic).")

        note_text = "\n".join(note) if note else "✅ Đã chạy xong."

        return (
            "### 🖥️ Kết quả chạy script cục bộ\n"
            f"- Interpreter: `{interpreter}`\n"
            f"- Args: `{args or '(none)'}`\n"
            f"- Return code: {rc}\n"
            f"- File tạm: `{tmp_path}`\n\n"
            f"**Stdout:**\n```\n{stdout[:4000] if stdout else ''}\n```\n"
            f"**Stderr:**\n```\n{stderr[:4000] if stderr else ''}\n```\n"
            f"**Ghi chú:** {note_text}\n"
        )

    except subprocess.TimeoutExpired:
        return (
            "❌ Script timeout.\n"
            f"- Timeout: {timeout}s\n"
            f"- Args: `{args}`\n"
        )
    except Exception as e:
        return f"❌ Lỗi khi chạy script cục bộ: {e}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
