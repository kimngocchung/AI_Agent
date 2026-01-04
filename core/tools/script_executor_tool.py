# File: core/tools/script_executor_tool.py
"""
Script Executor Tool - Cho phép AI tạo và đề xuất chạy script trên Kali
Yêu cầu xác nhận từ user trước khi thực thi
"""

import os
import difflib
import requests
from langchain_core.tools import tool
from dotenv import load_dotenv
from typing import Optional, List

load_dotenv()
KALI_LISTENER_URL = os.getenv("KALI_LISTENER_URL", "http://192.168.1.100:5000")


# === AI-POWERED ANALYSIS FUNCTIONS ===

def analyze_script_with_ai(script_content: str, target: str) -> str:
    """
    Sử dụng Gemini AI để phân tích script security.
    Trả về mô tả chi tiết cách script hoạt động.
    """
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "*Thiếu GEMINI_API_KEY để phân tích chi tiết.*\n"
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Lấy 500 dòng đầu của script để phân tích (tránh quá dài)
        script_preview = "\n".join(script_content.split("\n")[:500])
        
        prompt = f"""Bạn là chuyên gia bảo mật. Phân tích script Python/Bash sau và giải thích NGẮN GỌN:

**Script (trích đoạn):**
```
{script_preview}
```

**Mục tiêu:** {target}

**Yêu cầu phân tích:**
1. **Mục tiêu lỗ hổng:** Script này kiểm tra lỗ hổng gì? (CVE ID, tên lỗ hổng, phiên bản bị ảnh hưởng)
2. **Cơ chế hoạt động:** Script phát hiện lỗ hổng bằng cách nào? (HTTP method, payload, headers)
3. **Điều kiện vulnerable:** Khi nào script xác định target là vulnerable? (response code, content)

Trả lời NGẮN GỌN bằng tiếng Việt, format markdown với bullet points. Tối đa 15 dòng."""

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"[AI Script Analysis Error] {e}")
        return f"*Lỗi phân tích AI: {str(e)[:100]}*\n"


def analyze_results_with_ai(script_name: str, output: str, target: str) -> str:
    """
    Sử dụng Gemini AI để phân tích kết quả scan.
    Trả về đánh giá và khuyến nghị.
    """
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "*Thiếu GEMINI_API_KEY để phân tích kết quả.*\n"
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Giới hạn output để tránh quá dài
        output_preview = output[:3000] if output else "(Không có output)"
        
        prompt = f"""Bạn là chuyên gia bảo mật. Phân tích kết quả scan sau:

**Script:** {script_name}
**Target:** {target}

**Kết quả scan:**
```
{output_preview}
```

**Yêu cầu:**
1. **Đánh giá:** Target có vulnerable không? Mức độ nghiêm trọng?
2. **Giải thích:** Dựa vào output, giải thích TẠI SAO target vulnerable hoặc không vulnerable.
3. **Khuyến nghị:** 3 hành động cụ thể cần làm ngay.

Trả lời NGẮN GỌN bằng tiếng Việt, format markdown. Tối đa 12 dòng."""

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        print(f"[AI Results Analysis Error] {e}")
        return f"*Lỗi phân tích AI: {str(e)[:100]}*\n"


def analyze_execution_result(output: str, error: str, success: bool) -> dict:
    """
    Phân tích kết quả thực thi để xác định có lỗi không và loại lỗi.
    Returns dict with: is_error, is_fixable, error_type, error_message
    """
    result = {
        "is_error": False,
        "is_fixable": False,
        "error_type": None,
        "error_message": None,
        "is_success": success
    }
    
    # QUAN TRỌNG: Nếu success=True VÀ có output scan thành công → KHÔNG phải lỗi
    if success:
        # Check for successful scan indicators
        if "[VULNERABLE]" in output or "[NOT VULNERABLE]" in output or "SCAN SUMMARY" in output:
            result["is_success"] = True
            result["is_error"] = False
            return result
    
    combined = f"{output} {error}".lower()
    
    # Các loại lỗi có thể fix được - chỉ check trong error hoặc khi success=False
    fixable_errors = {
        "url_error": ["bad request", "invalid url", "malformed"],
        "syntax_error": [
            "syntaxerror", "indentationerror", "invalid syntax", "nameerror",
            "unexpected eof", "unexpected end", "unterminated", "incomplete input",
            "expected ':'", "expected ','", "expected ')'", "expected identifier"
        ],
        "import_error": ["modulenotfounderror", "importerror", "no module named"],
        "argument_error": ["unrecognized arguments", "error: argument", "invalid choice"],
        "type_error": ["typeerror", "attributeerror", "keyerror"],
    }
    
    # Các lỗi không thể fix - chỉ check khi success=False và có error output
    unfixable_errors = {
        "connection_error": ["connection refused", "cannot connect", "unreachable"],
        "permission_error": ["permission denied", "access denied"],
        "target_error": ["host not found", "name resolution", "dns"],
        "timeout_error": ["request timed out", "timeout expired"],
    }
    
    # Chỉ check errors nếu success=False hoặc có error output
    if not success or (error and len(error) > 10):
        # Check lỗi fixable (ưu tiên cao hơn)
        for error_type, patterns in fixable_errors.items():
            for pattern in patterns:
                if pattern in combined:
                    result["is_error"] = True
                    result["is_fixable"] = True
                    result["error_type"] = error_type
                    result["error_message"] = error[:500] if error else output[:500]
                    return result
        
        # Check lỗi unfixable
        for error_type, patterns in unfixable_errors.items():
            for pattern in patterns:
                if pattern in combined:
                    result["is_error"] = True
                    result["is_fixable"] = False
                    result["error_type"] = error_type
                    result["error_message"] = error[:500] if error else output[:500]
                    return result
        
        # Nếu không có lỗi rõ ràng nhưng success=False
        if not success and not output:
            result["is_error"] = True
            result["is_fixable"] = False
            result["error_type"] = "unknown"
            result["error_message"] = error[:500] if error else "Unknown error"
    
    return result


def fix_script_based_on_error(script_content: str, error_analysis: dict, target: str) -> str:
    """
    Gọi AI để sửa script dựa trên lỗi đã phát hiện.
    Returns: fixed script content or empty string if cannot fix
    """
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("[Fix Script] Missing GEMINI_API_KEY")
            return ""
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        error_type = error_analysis.get("error_type", "unknown")
        error_msg = error_analysis.get("error_message", "")
        
        prompt = f"""Bạn là chuyên gia Python. Script sau bị lỗi khi chạy. Hãy sửa lỗi.

**LOẠI LỖI:** {error_type}
**THÔNG BÁO LỖI:** {error_msg}
**TARGET:** {target}

**SCRIPT BỊ LỖI:**
```python
{script_content[:8000]}
```

**YÊU CẦU:**
1. Phân tích nguyên nhân lỗi
2. Sửa script để không còn lỗi
3. Trả về TOÀN BỘ script đã sửa trong block ```python ... ```
4. KHÔNG giải thích, CHỈ trả về code

**QUAN TRỌNG:**
- Giữ nguyên tất cả \\r\\n trong multipart payloads
- Đảm bảo tất cả f-strings đóng đúng cách
"""

        response = model.generate_content(prompt)
        fixed_output = response.text
        
        # Extract code from response
        import re
        code_match = re.search(r'```python\s*(.*?)```', fixed_output, re.DOTALL)
        if code_match:
            fixed_script = code_match.group(1).strip()
            print(f"[Fix Script] Successfully generated fix ({len(fixed_script)} chars)")
            return fixed_script
        
        print("[Fix Script] No python code block found in response")
        return ""
        
    except Exception as e:
        print(f"[Fix Script Error] {e}")
        return ""


def summarize_code_change(old_script: str, new_script: str, limit: int = 160) -> str:
    """
    T óm t t thay đ i gi ái mã giữa hai phiên bản script (ngắn gọn).
    """
    if not old_script:
        return ""
    diff = list(difflib.unified_diff(
        old_script.splitlines(),
        new_script.splitlines(),
        lineterm=""
    ))
    if not diff:
        return "dY-‹,? Không thấy thay đ i so với bản trước."
    # Lấy một phần diff để tránh quá dài
    trimmed = diff[:limit]
    if len(diff) > limit:
        trimmed.append(f"... ({len(diff) - limit} dòng diff bị cắt bớt)")
    return "```diff\n" + "\n".join(trimmed) + "\n```"


@tool
def propose_exploit_script(
    script_content: str = "",
    script_type: str = "python",
    description: str = "",
    target: str = "",
    script_name: str = ""
) -> str:
    """
    Đề xuất một script khai thác để user xác nhận trước khi chạy trên Kali.
    
    AI nên sử dụng tool này khi:
    - User yêu cầu chạy script có sẵn trong hệ thống (dùng script_name)
    - User yêu cầu tạo script khai thác CVE cụ thể (dùng script_content)
    - Cần chạy code tùy chỉnh dựa trên thông tin từ RAG
    
    Args:
        script_content (str): Nội dung script (nếu tự viết hoặc copy)
        script_type (str): Loại script - "python" hoặc "bash"
        description (str): Mô tả ngắn về mục đích của script
        target (str): URL/IP mục tiêu (nếu có)
        script_name (str): Tên script có sẵn trong scripts/ folder (ví dụ: "Scanner")
                          Nếu có, sẽ tự động load script từ file thay vì dùng script_content
        
    Returns:
        str: Thông báo yêu cầu xác nhận từ user với mã script
    """
    
    # Nếu có script_name, load từ file
    if script_name and not script_content:
        try:
            from utils.tool_loader import load_tool_by_name
            tool = load_tool_by_name(script_name)
            if tool:
                script_content = tool['content']
                script_type = tool['type']
                print(f"--- [Script Executor] Auto-loaded script: {script_name} ({tool['lines']} lines) ---")
            else:
                return f"❌ Không tìm thấy script '{script_name}' trong hệ thống. Hãy kiểm tra lại tên script."
        except Exception as e:
            return f"❌ Lỗi khi load script: {e}"
    
    if not script_content:
        return "❌ Cần cung cấp script_content hoặc script_name."
    
    print(f"--- [Script Executor] Đề xuất script {script_type} ---")
    print(f"    Target: {target}")
    print(f"    Description: {description}")
    
    # Truncate script cho hiển thị (giữ nguyên trong proposal data)
    script_lines = script_content.split('\n')
    if len(script_lines) > 50:
        truncated_script = '\n'.join(script_lines[:50]) + f"\n\n# ... [{len(script_lines) - 50} dòng còn lại đã ẩn để UI nhanh hơn] ..."
    else:
        truncated_script = script_content
    
    # Trả về thông báo để hiển thị trong chat
    # Format đặc biệt để app.py nhận diện và hiển thị UI xác nhận
    args_value = f"-u {target}" if target else ""
    return f"""__SCRIPT_PROPOSAL__
{{
    "type": "{script_type}",
    "description": "{description}",
    "target": "{target}",
    "args": "{args_value}",
    "script": {repr(script_content)}
}}
__END_SCRIPT_PROPOSAL__

📋 **Script đề xuất ({script_type.upper()}):**

**Mô tả:** {description}
**Mục tiêu:** {target or "Chưa xác định"}
**Độ dài:** {len(script_lines)} dòng

```{script_type}
{truncated_script}
```

⚠️ **Xác nhận:** Bạn có muốn chạy script này trên Kali Linux không? (Trả lời 'có')
"""


def execute_script_on_kali(script_content: str, script_type: str = "python", timeout: int = 300, args: str = "") -> dict:
    """
    Thực thi script trên Kali Linux (gọi sau khi user xác nhận)
    
    Args:
        script_content: Nội dung script
        script_type: "python" hoặc "bash"
        timeout: Thời gian chờ tối đa (giây)
        args: Tham số dòng lệnh cho script (ví dụ: "-u https://target.com")
        
    Returns:
        dict với keys: success, output, error_output
    """
    
    print(f"--- [Script Executor] Đang gửi script đến Kali ---")
    print(f"    Args: {args}")
    
    api_endpoint = f"{KALI_LISTENER_URL}/execute_script"
    
    payload = {
        "script": script_content,
        "type": script_type,
        "timeout": timeout,
        "args": args  # Thêm args
    }
    
    try:
        response = requests.post(api_endpoint, json=payload, timeout=timeout + 10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("success"):
            print("--- [Script Executor] Thực thi thành công ---")
            return {
                "success": True,
                "output": data.get("output", ""),
                "error_output": data.get("error_output", "")
            }
        else:
            print(f"--- [Script Executor] Lỗi: {data.get('error_output')} ---")
            return {
                "success": False,
                "output": data.get("output", ""),
                "error_output": data.get("error_output", "Script execution failed")
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "output": "",
            "error_output": f"Timeout: Script chạy quá {timeout} giây"
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "output": "",
            "error_output": f"Không thể kết nối đến Kali Listener tại {api_endpoint}"
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error_output": f"Lỗi: {str(e)}"
        }


@tool
def run_script_with_analysis(
    script_name: str,
    target: str,
    args: str = "",
    description: str = ""
) -> str:
    """
    Chạy script có sẵn trên Kali VÀ phân tích kết quả.
    KHÔNG yêu cầu xác nhận - TỰ ĐỘNG CHẠY LUÔN.
    
    Tool này sẽ:
    1. Load script từ scripts/ folder
    2. Phân tích script và giải thích cho user
    3. Chạy script trên Kali với target và args
    4. Nhận kết quả và phân tích
    5. Trả về kết quả + phân tích
    
    Args:
        script_name: Tên script có sẵn (ví dụ: "Scanner", "scanner_v2")
        target: URL/IP mục tiêu
        args: Command line arguments (ví dụ: "--read-file /etc/passwd", "--safe-check")
        description: Mô tả mục đích (tùy chọn)
        
    Returns:
        str: Phân tích script + Kết quả chạy + Phân tích kết quả
    """
    
    print(f"--- [Auto Run] Script: {script_name} ---")
    print(f"--- [Auto Run] Target: {target} ---")
    print(f"--- [Auto Run] Args: {args} ---")
    
    # 1. Load script
    try:
        from utils.tool_loader import load_tool_by_name
        loaded = load_tool_by_name(script_name)
        if not loaded:
            return f"❌ Không tìm thấy script '{script_name}'. Hãy upload script trước."
        
        script_content = loaded['content']
        script_type = loaded['type']
        script_lines = loaded['lines']
        
        print(f"--- [Auto Run] Loaded: {loaded['name']} ({script_lines} lines) ---")
    except Exception as e:
        return f"❌ Lỗi load script: {e}"
    
    # 2. Phân tích script bằng AI
    script_analysis = f"""
## 📄 Script: {loaded['name']}

**Loại:** {script_type.upper()}
**Độ dài:** {script_lines} dòng
**Mục tiêu:** {target}

### 🔍 Phân tích Script (bởi AI):

"""
    
    # Gọi AI để phân tích script
    try:
        ai_script_analysis = analyze_script_with_ai(script_content, target)
        script_analysis += ai_script_analysis
    except Exception as e:
        print(f"[AI Analysis Error] {e}")
        # Fallback nếu AI fail
        script_analysis += f"*Không thể phân tích chi tiết. Script có {script_lines} dòng code.*\n"
    
    script_analysis += f"\n---\n\n### 🚀 Đang chạy script trên Kali...\n"
    
    # 3. Chạy script trên Kali VỚI RETRY LOOP
    MAX_RETRIES = 3
    current_script = script_content
    full_args = f"-u {target}" if target.startswith(("http://", "https://")) else ""
    if args:
        full_args = f"{full_args} {args}".strip()
    
    print(f"--- [Auto Run] Full args: {full_args} ---")
    
    result_section = ""
    analysis_section = ""
    
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"--- [Auto Run] Attempt {attempt}/{MAX_RETRIES} ---")
        
        result = execute_script_on_kali(
            script_content=current_script,
            script_type=script_type,
            args=full_args,
            timeout=120
        )
        
        output = result.get("output", "").strip()
        error = result.get("error_output", "").strip()
        success = result.get("success", False)
        
        # Phân tích kết quả
        error_analysis = analyze_execution_result(output, error, success)
        
        # Nếu thành công hoặc lỗi không fix được → dừng
        if not error_analysis["is_error"]:
            print(f"--- [Auto Run] SUCCESS on attempt {attempt} ---")
            no_output_hint = ""
            # Nếu không có output, thử tự động chạy lại với vài cấu hình khác (tối đa 2 lần) trước khi trả kết quả
            if not output:
                fallback_runs = []
                if "--verbose" not in full_args:
                    fallback_runs.append(f"{full_args} --verbose".strip())
                if "--safe-check" not in full_args:
                    fallback_runs.append(f"{full_args} --safe-check".strip())

                for fb_idx, fb_args in enumerate(fallback_runs, start=1):
                    print(f"--- [Auto Run] No output -> retry with fallback args #{fb_idx}: {fb_args} ---")
                    retry_result = execute_script_on_kali(
                        script_content=current_script,
                        script_type=script_type,
                        args=fb_args,
                        timeout=120
                    )
                    retry_out = retry_result.get("output", "").strip()
                    retry_err = retry_result.get("error_output", "").strip()
                    if retry_out:
                        output = retry_out
                        error = retry_err
                        full_args = fb_args  # cập nhật để hiển thị trong báo cáo
                        break

                if not output:
                    no_output_hint = (
                        "\n⚠️ Script chạy thành công nhưng không có output hiển thị. "
                        "Đã thử tự chạy lại với các cấu hình fallback nhưng vẫn không có log. "
                        "Kiểm tra log của Kali listener hoặc chạy lại với tham số phù hợp/`--help`/`--verbose` "
                        f"(args đã dùng: \"{full_args or '(none)'}\")."
                    )
            result_section = f"""
### 🖥️ Kết quả từ Kali (lần thử {attempt}):

**Trạng thái:** ✅ Thành công

```
{output[:5000] if output else "(Không có output)"}
```
{no_output_hint}
"""
            # Phân tích kết quả thành công
            analysis_section = "\n### 🧠 Phân tích kết quả (bởi AI):\n\n"
            try:
                ai_result_analysis = analyze_results_with_ai(loaded['name'], output, target)
                analysis_section += ai_result_analysis
            except Exception as e:
                print(f"[AI Results Analysis Error] {e}")
                if "[VULNERABLE]" in output:
                    analysis_section += "⚠️ **PHÁT HIỆN LỖ HỔNG!** Target có thể bị tấn công.\n"
                elif "[NOT VULNERABLE]" in output:
                    analysis_section += "✅ **KHÔNG PHÁT HIỆN LỖ HỔNG** trong phạm vi kiểm tra.\n"
                else:
                    analysis_section += "📊 Script đã chạy thành công. Xem output ở trên.\n"
            break
        
        elif not error_analysis["is_fixable"]:
            print(f"--- [Auto Run] UNFIXABLE ERROR: {error_analysis['error_type']} ---")
            result_section = f"""
### 🖥️ Kết quả từ Kali (lần thử {attempt}):

**Trạng thái:** ❌ Lỗi không thể tự sửa

**Loại lỗi:** {error_analysis['error_type']}

```
{error[:2000] if error else output[:2000]}
```
"""
            analysis_section = f"\n### 🧠 Phân tích lỗi:\n\n❌ **{error_analysis['error_type'].upper()}:** Lỗi này cần user can thiệp thủ công.\n"
            break
        
        else:
            # Lỗi có thể fix được → thử sửa
            print(f"--- [Auto Run] FIXABLE ERROR: {error_analysis['error_type']} - attempting fix... ---")

            if attempt < MAX_RETRIES:
                fixed_script = fix_script_based_on_error(current_script, error_analysis, target)

                if fixed_script:
                    diff_view = summarize_code_change(current_script, fixed_script)
                    current_script = fixed_script
                    if diff_view:
                        script_analysis += "\n#### 🔄 Tóm tắt thay đổi code:\n" + diff_view + "\n"
                    try:
                        script_analysis += "\n#### 🔍 Phân tích script sau khi sửa:\n"
                        script_analysis += analyze_script_with_ai(current_script, target)
                    except Exception as e:
                        print(f"[AI Re-Analysis Error] {e}")
                    script_analysis += f"\n🔧 **Lần {attempt} thất bại** - AI đang sửa lỗi `{error_analysis['error_type']}` và thử lại...\n"
                    continue
                else:
                    # Không fix được
                    result_section = f"""
### 🖥️ Kết quả từ Kali:

**Trạng thái:** ❌ Lỗi - Không thể tự sửa

```
{error[:2000] if error else output[:2000]}
```
"""
                    analysis_section = "\n### 🧠 Phân tích:\n\n❌ AI không thể tự sửa lỗi này.\n"
                    break
            else:
                # Hết số lần thử
                result_section = f"""
### 🖥️ Kết quả từ Kali (đã thử {MAX_RETRIES} lần):

**Trạng thái:** ❌ Thất bại sau {MAX_RETRIES} lần thử

```
{error[:2000] if error else output[:2000]}
```
"""
                analysis_section = f"\n### 🧠 Phân tích:\n\n❌ Script vẫn lỗi sau {MAX_RETRIES} lần thử sửa. Vui lòng kiểm tra thủ công.\n"
    
    return script_analysis + result_section + analysis_section
