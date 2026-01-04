# File: core/tools/auto_script_tool.py
"""
Auto Script Tool - Unified Generate + Run + Fix Loop

Tool này cho phép AI Agent:
1. Tạo script mới dựa trên script gốc + yêu cầu user
2. Chạy script ngay trên terminal local (không cần Kali)
3. Phân tích kết quả (dù lỗi hay thành công)
4. Nếu lỗi → AI phân tích, sửa script, chạy lại (auto-retry loop)
5. Trả kết quả cuối cùng về giao diện cho user
"""

import os
import sys
import re
import subprocess
import tempfile
import shlex
import time
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

# Import từ các module khác
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from utils.script_validator import validate_script, format_validation_result
from utils.tool_loader import load_tool_by_name, get_available_tools


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class ExecutionResult:
    """Kết quả thực thi script"""
    success: bool
    return_code: int
    stdout: str
    stderr: str
    execution_time: float
    error_type: Optional[str] = None  # "syntax", "import", "runtime", "timeout", "unknown"


@dataclass
class FixAttempt:
    """Một lần thử sửa lỗi"""
    attempt_number: int
    error_analysis: str
    fix_strategy: str
    script_diff_summary: str
    result: ExecutionResult


# ==============================================================================
# LOCAL EXECUTION
# ==============================================================================

def execute_script_locally(
    script_content: str,
    script_type: str = "python",
    args: str = "",
    timeout: int = 180
) -> ExecutionResult:
    """
    Chạy script trên máy local và trả về kết quả có cấu trúc.
    
    Args:
        script_content: Nội dung script
        script_type: "python" hoặc "bash"
        args: Arguments dòng lệnh
        timeout: Timeout tính bằng giây
        
    Returns:
        ExecutionResult với đầy đủ thông tin
    """
    if not script_content:
        return ExecutionResult(
            success=False,
            return_code=-1,
            stdout="",
            stderr="Thiếu script_content",
            execution_time=0,
            error_type="unknown"
        )
    
    script_type = script_type.lower()
    suffix = ".py" if script_type == "python" else ".sh"
    interpreter = "python" if script_type == "python" else "bash"
    
    tmp_path = None
    start_time = time.time()
    
    try:
        # Tạo file tạm
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as tmp:
            tmp.write(script_content)
            tmp_path = tmp.name
        
        if script_type == "bash":
            os.chmod(tmp_path, 0o755)
        
        # Build command
        cmd = [interpreter, tmp_path]
        if args:
            cmd.extend(shlex.split(args))
        
        # Execute
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )
        
        execution_time = time.time() - start_time
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        
        # Xác định loại lỗi
        error_type = None
        if proc.returncode != 0:
            error_type = classify_error(stderr, stdout)
        
        return ExecutionResult(
            success=(proc.returncode == 0),
            return_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            execution_time=execution_time,
            error_type=error_type
        )
        
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            success=False,
            return_code=-1,
            stdout="",
            stderr=f"Script timeout sau {timeout} giây",
            execution_time=timeout,
            error_type="timeout"
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            return_code=-1,
            stdout="",
            stderr=str(e),
            execution_time=time.time() - start_time,
            error_type="unknown"
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except:
                pass


def classify_error(stderr: str, stdout: str) -> str:
    """Phân loại loại lỗi dựa trên output"""
    combined = f"{stderr} {stdout}".lower()
    
    if any(kw in combined for kw in ["syntaxerror", "indentationerror", "invalid syntax", "unexpected eof"]):
        return "syntax"
    elif any(kw in combined for kw in ["modulenotfounderror", "importerror", "no module named"]):
        return "import"
    elif any(kw in combined for kw in ["typeerror", "attributeerror", "nameerror", "keyerror", "valueerror"]):
        return "runtime"
    elif any(kw in combined for kw in ["connectionerror", "timeout", "unreachable"]):
        return "network"
    else:
        return "unknown"


# ==============================================================================
# AI ANALYSIS FUNCTIONS
# ==============================================================================

def get_ai_model():
    """Lấy instance của Gemini model"""
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY không được tìm thấy")
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def analyze_error_with_ai(
    stderr: str,
    stdout: str,
    script_content: str,
    error_type: str
) -> str:
    """
    AI phân tích lỗi và đưa ra nhận định.
    
    Returns:
        Chuỗi phân tích chi tiết về nguyên nhân lỗi
    """
    try:
        model = get_ai_model()
        
        prompt = f"""Bạn là chuyên gia Python. Phân tích lỗi sau và giải thích NGẮN GỌN (tối đa 5 dòng):

**LOẠI LỖI:** {error_type}

**STDERR:**
```
{stderr[:2000]}
```

**STDOUT:**
```
{stdout[:1000]}
```

**SCRIPT (trích đoạn cuối):**
```python
{script_content[-1500:]}
```

**YÊU CẦU:**
1. Xác định chính xác dòng và nguyên nhân lỗi
2. Giải thích vì sao xảy ra
3. KHÔNG đề xuất cách sửa (sẽ làm ở bước sau)

Trả lời bằng tiếng Việt, ngắn gọn."""

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Không thể phân tích lỗi với AI: {e}"


def generate_fix_strategy_with_ai(
    error_analysis: str,
    script_content: str,
    stderr: str,
    previous_attempts: list = None
) -> str:
    """
    AI đề xuất chiến lược sửa lỗi.
    
    Returns:
        Chiến lược sửa lỗi chi tiết
    """
    try:
        model = get_ai_model()
        
        previous_context = ""
        if previous_attempts:
            previous_context = "\n**CÁC LẦN SỬA TRƯỚC (ĐÃ THẤT BẠI):**\n"
            for attempt in previous_attempts[-3:]:  # Lấy 3 lần gần nhất
                previous_context += f"- Lần {attempt.attempt_number}: {attempt.fix_strategy[:100]}...\n"
            previous_context += "\n⚠️ PHẢI sử dụng cách tiếp cận KHÁC hoàn toàn!\n"
        
        prompt = f"""Bạn là chuyên gia Python. Đề xuất chiến lược SỬA LỖI cụ thể.

**PHÂN TÍCH LỖI:**
{error_analysis}

**STDERR:**
```
{stderr[:1000]}
```
{previous_context}
**YÊU CẦU:**
1. Đề xuất chiến lược sửa cụ thể (không phải code, chỉ mô tả)
2. Nếu là lỗi import → chỉ ra cách thay thế hoặc cài đặt
3. Nếu là lỗi syntax → chỉ ra dòng cần sửa và cách sửa
4. Nếu là lỗi runtime → chỉ ra logic cần thay đổi

Trả lời bằng tiếng Việt, dưới dạng bullet points ngắn gọn."""

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Không thể tạo chiến lược sửa: {e}"


def apply_fix_with_ai(
    script_content: str,
    error_analysis: str,
    fix_strategy: str,
    stderr: str
) -> Tuple[str, str]:
    """
    AI áp dụng sửa lỗi vào script.
    
    Returns:
        (fixed_script, diff_summary)
    """
    try:
        model = get_ai_model()
        
        prompt = f"""Bạn là chuyên gia Python. SỬA script theo chiến lược sau.

**PHÂN TÍCH LỖI:**
{error_analysis}

**CHIẾN LƯỢC SỬA:**
{fix_strategy}

**STDERR:**
```
{stderr[:1000]}
```

**SCRIPT CẦN SỬA:**
```python
{script_content}
```

**YÊU CẦU QUAN TRỌNG:**
1. Trả về TOÀN BỘ script đã sửa trong block ```python ... ```
2. Giữ nguyên logic chính, CHỈ sửa lỗi
3. Nếu thiếu module → thay bằng cách khác hoặc thêm try/except
4. Đảm bảo script có thể chạy được

**CHỈ TRẢ VỀ CODE, KHÔNG GIẢI THÍCH.**"""

        response = model.generate_content(prompt)
        output = response.text
        
        # Extract code
        fixed_script = ""
        code_match = re.search(r'```python\s*(.*?)```', output, re.DOTALL)
        if code_match:
            fixed_script = code_match.group(1).strip()
        else:
            code_match = re.search(r'```\s*(.*?)```', output, re.DOTALL)
            if code_match:
                fixed_script = code_match.group(1).strip()
        
        if not fixed_script:
            # Fallback: nếu không có code block, lấy toàn bộ output
            if output.strip().startswith("#!/") or "import " in output[:100]:
                fixed_script = output.strip()
            else:
                return script_content, "Không thể extract code từ AI response"
        
        # Tạo diff summary ngắn gọn
        old_lines = len(script_content.split('\n'))
        new_lines = len(fixed_script.split('\n'))
        diff_summary = f"Script: {old_lines} → {new_lines} dòng"
        
        return fixed_script, diff_summary
        
    except Exception as e:
        return script_content, f"Lỗi khi áp dụng sửa: {e}"


def analyze_success_with_ai(
    stdout: str,
    stderr: str,
    target: str,
    script_name: str
) -> str:
    """
    AI phân tích kết quả chạy thành công.
    
    Returns:
        Phân tích kết quả chi tiết
    """
    try:
        model = get_ai_model()
        
        prompt = f"""Bạn là chuyên gia bảo mật. Phân tích kết quả scan sau:

**SCRIPT:** {script_name}
**TARGET:** {target}

**STDOUT:**
```
{stdout[:4000]}
```

**STDERR (nếu có):**
```
{stderr[:1000] if stderr else "(Không có)"}
```

**YÊU CẦU:**
1. **TÓM TẮT:** Kết quả chính (vulnerable hay không?)
2. **CHI TIẾT:** Giải thích ý nghĩa output
3. **KHUYẾN NGHỊ:** 2-3 hành động tiếp theo

Trả lời bằng tiếng Việt, format markdown. Tối đa 15 dòng."""

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"Không thể phân tích kết quả: {e}"


# ==============================================================================
# SCRIPT GENERATION
# ==============================================================================

def generate_script_from_base(
    request: str,
    base_script_content: str,
    base_script_name: str,
    target: str
) -> Tuple[str, str]:
    """
    Tạo script mới từ script gốc theo yêu cầu user.
    
    Returns:
        (generated_script, generation_summary)
    """
    try:
        model = get_ai_model()
        
        prompt = f"""Bạn là chuyên gia Python viết script bảo mật.

**YÊU CẦU USER:** {request}

**SCRIPT GỐC ({base_script_name}):**
```python
{base_script_content[:8000]}
```

**TARGET:** {target}

**NHIỆM VỤ:**
1. Dựa trên script gốc, TẠO SCRIPT MỚI đáp ứng yêu cầu user
2. Giữ nguyên cấu trúc và logic chính
3. Thêm/sửa chức năng theo yêu cầu
4. Đảm bảo script có thể chạy được ngay

**YÊU CẦU OUTPUT:**
- Trả về TOÀN BỘ script trong block ```python ... ```
- Script phải có if __name__ == "__main__": main()
- Phải có argparse với -u/--url cho target

**CHỈ TRẢ VỀ CODE, KHÔNG GIẢI THÍCH.**"""

        response = model.generate_content(prompt)
        output = response.text
        
        # Extract code
        generated_script = ""
        code_match = re.search(r'```python\s*(.*?)```', output, re.DOTALL)
        if code_match:
            generated_script = code_match.group(1).strip()
        
        if not generated_script:
            return base_script_content, "Không thể tạo script mới, sử dụng script gốc"
        
        summary = f"Đã tạo script mới từ {base_script_name} ({len(generated_script.split(chr(10)))} dòng)"
        return generated_script, summary
        
    except Exception as e:
        return base_script_content, f"Lỗi tạo script: {e}"


# ==============================================================================
# MAIN TOOL
# ==============================================================================

@tool
def auto_generate_and_run(
    request: str,
    target: str,
    base_script_name: str,
    args: str = "",
    max_retries: int = 5,
    timeout: int = 180
) -> str:
    """
    Tự động tạo script từ script gốc, chạy local, và sửa lỗi nếu cần.
    
    Tool này thực hiện workflow hoàn chỉnh:
    1. Load script gốc từ scripts/ folder
    2. Tạo script mới theo yêu cầu user (nếu có yêu cầu cụ thể)
    3. Validate syntax
    4. Chạy script trên terminal LOCAL (không qua Kali)
    5. Nếu lỗi: AI phân tích → đề xuất sửa → áp dụng → chạy lại
    6. Lặp lại tối đa max_retries lần
    7. Trả về kết quả và phân tích chi tiết
    
    Args:
        request: Yêu cầu của user (ví dụ: "kiểm tra target này", "thêm chức năng X")
        target: URL/IP mục tiêu
        base_script_name: Tên script gốc (ví dụ: "scanner", "Scanner")
        args: Arguments bổ sung cho script (ví dụ: "--safe-check")
        max_retries: Số lần retry tối đa (default: 5)
        timeout: Timeout mỗi lần chạy tính bằng giây (default: 180)
        
    Returns:
        Báo cáo chi tiết bao gồm: quá trình thực thi, các lần retry, kết quả cuối cùng
    """
    
    print(f"\n{'='*60}")
    print(f"🚀 [AUTO TOOL] Starting auto_generate_and_run")
    print(f"   Request: {request[:100]}...")
    print(f"   Target: {target}")
    print(f"   Base Script: {base_script_name}")
    print(f"   Args: {args}")
    print(f"   Max Retries: {max_retries}")
    print(f"{'='*60}\n")
    
    # 1. Load script gốc
    loaded = load_tool_by_name(base_script_name)
    if not loaded:
        available = get_available_tools()
        available_names = [t['name'] for t in available] if available else []
        return f"""❌ **Không tìm thấy script:** `{base_script_name}`

**Scripts có sẵn:** {', '.join(available_names) if available_names else 'Chưa có script nào'}

Hãy upload script hoặc kiểm tra lại tên."""
    
    base_script = loaded['content']
    script_type = loaded['type']
    
    print(f"✅ Loaded base script: {loaded['name']} ({loaded['lines']} lines)")
    
    # 2. Tạo script mới nếu có yêu cầu cụ thể
    current_script = base_script
    generation_summary = "Sử dụng script gốc không thay đổi"
    
    # Kiểm tra xem user có yêu cầu tạo/sửa script không
    modify_keywords = ["tạo", "viết", "thêm", "sửa", "cải tiến", "modify", "add", "create", "improve"]
    if any(kw in request.lower() for kw in modify_keywords):
        print("📝 Generating new script based on request...")
        current_script, generation_summary = generate_script_from_base(
            request, base_script, base_script_name, target
        )
        print(f"   {generation_summary}")
    
    # 3. Validate syntax trước
    validation = validate_script(current_script, script_type)
    if not validation.is_valid:
        print(f"⚠️ Initial validation failed, attempting auto-fix...")
        # Thử sửa syntax ngay từ đầu
        fixed, diff = apply_fix_with_ai(
            current_script,
            "Lỗi syntax được phát hiện trong validation",
            "\n".join(validation.errors),
            ""
        )
        current_script = fixed
        validation = validate_script(current_script, script_type)
    
    # 4. Build full args
    full_args = ""
    if target:
        # Kiểm tra xem target có phải URL không
        if target.startswith(("http://", "https://")):
            full_args = f"-u {target}"
        else:
            full_args = f"--url {target}"
    if args:
        full_args = f"{full_args} {args}".strip()
    
    print(f"🔧 Full args: {full_args}")
    
    # 5. Retry loop
    fix_attempts: list[FixAttempt] = []
    final_result: Optional[ExecutionResult] = None
    final_analysis = ""
    
    for attempt in range(1, max_retries + 1):
        print(f"\n--- Attempt {attempt}/{max_retries} ---")
        
        # Execute
        result = execute_script_locally(
            current_script,
            script_type,
            full_args,
            timeout
        )
        
        print(f"   Return code: {result.return_code}")
        print(f"   Execution time: {result.execution_time:.2f}s")
        print(f"   Error type: {result.error_type}")
        
        # Check success
        if result.success or (result.return_code == 0):
            print(f"✅ SUCCESS on attempt {attempt}")
            final_result = result
            
            # Phân tích kết quả thành công
            final_analysis = analyze_success_with_ai(
                result.stdout,
                result.stderr,
                target,
                base_script_name
            )
            break
        
        # Handle failure
        if attempt >= max_retries:
            print(f"❌ Max retries ({max_retries}) reached")
            final_result = result
            final_analysis = f"**Đã thử {max_retries} lần nhưng vẫn thất bại.**\n\nLỗi cuối cùng: {result.error_type}"
            break
        
        # AI phân tích lỗi
        print(f"🔍 Analyzing error...")
        error_analysis = analyze_error_with_ai(
            result.stderr,
            result.stdout,
            current_script,
            result.error_type or "unknown"
        )
        
        # AI đề xuất chiến lược sửa
        print(f"💡 Generating fix strategy...")
        fix_strategy = generate_fix_strategy_with_ai(
            error_analysis,
            current_script,
            result.stderr,
            fix_attempts
        )
        
        # AI áp dụng sửa
        print(f"🔧 Applying fix...")
        fixed_script, diff_summary = apply_fix_with_ai(
            current_script,
            error_analysis,
            fix_strategy,
            result.stderr
        )
        
        # Lưu attempt
        fix_attempts.append(FixAttempt(
            attempt_number=attempt,
            error_analysis=error_analysis,
            fix_strategy=fix_strategy,
            script_diff_summary=diff_summary,
            result=result
        ))
        
        # Update script cho lần sau
        current_script = fixed_script
        print(f"   {diff_summary}")
    
    # 6. Lưu script nếu thành công
    saved_info = ""
    if final_result and final_result.success:
        try:
            scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts')
            base_filename = base_script_name.lower().replace(" ", "_")
            
            # Tìm version tiếp theo
            version = 2
            while os.path.exists(os.path.join(scripts_dir, f"{base_filename}_v{version}.py")):
                version += 1
            
            new_filename = f"{base_filename}_v{version}.py"
            new_filepath = os.path.join(scripts_dir, new_filename)
            
            with open(new_filepath, 'w', encoding='utf-8') as f:
                f.write(current_script)
            
            saved_info = f"\n\n💾 **Script đã lưu:** `scripts/{new_filename}`"
            print(f"💾 Saved to: {new_filepath}")
            
        except Exception as e:
            saved_info = f"\n\n⚠️ Không thể lưu script: {e}"
    
    # 7. Build report
    report = f"""## 🤖 Auto Script Execution Report

### 📋 Thông tin
- **Script gốc:** `{base_script_name}` ({loaded['lines']} dòng)
- **Target:** `{target}`
- **Args:** `{full_args or "(none)"}`
- **Tạo script:** {generation_summary}

---

### 🔄 Quá trình thực thi

**Số lần thử:** {len(fix_attempts) + 1}/{max_retries}
"""
    
    # Chi tiết các lần fix
    if fix_attempts:
        report += "\n#### Các lần sửa lỗi:\n"
        for fa in fix_attempts:
            report += f"""
**Lần {fa.attempt_number}:**
- Lỗi: `{fa.result.error_type}`
- Phân tích: {fa.error_analysis[:200]}...
- Sửa: {fa.script_diff_summary}
"""
    
    # Kết quả cuối
    if final_result:
        status_icon = "✅" if final_result.success else "❌"
        status_text = "Thành công" if final_result.success else "Thất bại"
        
        report += f"""
---

### {status_icon} Kết quả cuối cùng: **{status_text}**

**Return code:** {final_result.return_code}
**Thời gian:** {final_result.execution_time:.2f}s

#### 📄 Output:
```
{final_result.stdout[:5000] if final_result.stdout else "(Không có output)"}
```
"""
        
        if final_result.stderr and not final_result.success:
            report += f"""
#### ⚠️ Stderr:
```
{final_result.stderr[:2000]}
```
"""
    
    # Phân tích AI
    report += f"""
---

### 🧠 Phân tích của AI:

{final_analysis}
{saved_info}
"""
    
    print(f"\n{'='*60}")
    print(f"🏁 [AUTO TOOL] Completed")
    print(f"{'='*60}\n")
    
    return report


# ==============================================================================
# HELPER TOOL - List scripts
# ==============================================================================

@tool
def list_scripts_for_auto_run() -> str:
    """
    Liệt kê các scripts có sẵn để sử dụng với auto_generate_and_run.
    
    Returns:
        Danh sách scripts với tên và mô tả
    """
    tools = get_available_tools()
    
    if not tools:
        return "📁 **Chưa có script nào.** Hãy upload script qua giao diện Sources."
    
    result = "## 📁 Scripts có sẵn cho Auto Run:\n\n"
    for t in tools:
        result += f"- **{t['name']}** (`{t['filename']}`) - {t['lines']} dòng\n"
        if t['description']:
            result += f"  _{t['description'][:100]}..._\n"
    
    result += "\n**Cách sử dụng:** `auto_generate_and_run(base_script_name=\"<tên script>\", target=\"<URL>\", request=\"<yêu cầu>\")`"
    
    return result


# ==============================================================================
# TEST
# ==============================================================================

if __name__ == "__main__":
    # Test execute locally
    test_script = '''
import sys
print("Hello from test script!")
print(f"Args: {sys.argv[1:]}")
'''
    
    result = execute_script_locally(test_script, "python", "--test arg1")
    print(f"Success: {result.success}")
    print(f"Output: {result.stdout}")
    print(f"Error: {result.stderr}")
