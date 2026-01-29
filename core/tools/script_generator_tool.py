# File: core/tools/script_generator_tool.py
"""
Script Generator Tool
Cho phép AI tạo script exploit tiên tiến dựa trên:
- Scripts user đã upload (scripts/ folder)
- Kiến thức từ RAG (thông tin CVE, payloads, techniques...)
- Yêu cầu cụ thể của user

AI sẽ phân tích script gốc và cải tiến dựa trên context từ RAG,
KHÔNG sử dụng templates chung để đảm bảo tính chính xác.
"""

import os
import re
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

# Import các module hỗ trợ
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from utils.script_validator import validate_script, format_validation_result
from utils.tool_loader import load_tool_by_name, get_available_tools


# ==============================================================================
# SCRIPT GENERATION PROMPT
# ==============================================================================

SCRIPT_GENERATION_PROMPT = """Bạn là chuyên gia viết script bảo mật/pentest với 15+ năm kinh nghiệm.

🇻🇳 **QUAN TRỌNG:** LUÔN TRẢ LỜI BẰNG TIẾNG VIỆT. Tất cả giải thích, comment phải bằng tiếng Việt.

## 🔴 CÁCH TƯ DUY ĐÚNG (QUAN TRỌNG!)

**LUÔN SUY NGHĨ THEO THỨ TỰ:**

1. **HIỂU YÊU CẦU USER:** User muốn đạt được gì? (đọc file, chạy lệnh, lấy dữ liệu...)
2. **PHÂN TÍCH SCRIPT GỐC:** Script đang làm gì? Có khả năng gì? (RCE, SQL, XSS...)
3. **TẬN DỤNG SCRIPT GỐC:** Sửa đổi tối thiểu để đáp ứng yêu cầu

**KHÔNG BAO GIỜ:**
- Tạo script hoàn toàn mới không liên quan đến script gốc
- Viết lại từ đầu khi chỉ cần thay đổi command/payload
- Bỏ qua thông tin từ RAG context (CVE details, payloads...)

## 🔥 HƯỚNG DẪN SỬA PAYLOAD RCE ĐỂ ĐỌC FILE:

Nếu script gốc có **RCE** (Remote Code Execution), bạn có thể đọc file bằng cách:

**TÌM trong script gốc:**
```python
# Tìm hàm build_rce_payload hoặc tương tự
cmd = 'echo $((41*271))'  # Lệnh hiện tại
```

**TẠO HÀM MỚI (KHÔNG sửa hàm cũ vì có f-strings phức tạp):**
```python
def build_file_read_payload(target_file: str, waf_bypass: bool = False, waf_bypass_size_kb: int = 128) -> tuple[str, str]:
    '''Đọc file từ xa bằng RCE - thay echo bằng cat'''
    boundary = "----WebKitFormBoundaryx8jO2oVc6SWP3Sad"
    
    # THAY ĐỔI QUAN TRỌNG: dùng cat thay vì echo
    cmd = f'cat {{target_file}}'
    
    # Phần còn lại GIỐNG HỆT build_rce_payload
    prefix_payload = (
        f"var res=process.mainModule.require('child_process').execSync('{{cmd}}')"
        # ... copy phần còn lại từ build_rce_payload
    )
    # ...
```

**THÊM ARGUMENT vào main():**
```python
parser.add_argument("--read-file", metavar="PATH", help="Đọc file từ xa (VD: /etc/passwd)")
```

**CẬP NHẬT check_vulnerability() để dùng payload mới:**
```python
elif args.read_file:
    body, content_type = build_file_read_payload(args.read_file, waf_bypass, waf_bypass_size_kb)
```

---

**NHIỆM VỤ:** Tạo script dựa trên script gốc để đáp ứng yêu cầu user.

**CÁCH LÀM:**

1. **PHÂN TÍCH** script gốc - hiểu cách nó hoạt động, nó có khả năng gì
2. **XÁC ĐỊNH** cần thêm/sửa gì để đáp ứng yêu cầu user (sửa tối thiểu)
3. **VIẾT SCRIPT** trong block ```python ... ```


**QUAN TRỌNG VỀ F-STRINGS VỚI \\r\\n:**
- KHÔNG sửa các hàm có f-strings với `\\r\\n` như `build_rce_payload`, `build_safe_payload`
- Thay vào đó, TẠO HÀM MỚI hoặc WRAPPER để thêm tính năng

**FORMAT OUTPUT BẮT BUỘC:**

```
## 📝 PHÂN TÍCH & CẢI TIẾN:

### Hiểu script gốc:
[Giải thích ngắn gọn cách script hoạt động]

### Cần thay đổi để đáp ứng yêu cầu:
1. [Thay đổi 1]
2. [Thay đổi 2]

---

### COMPLETE_SCRIPT:
```python
#!/usr/bin/env python3
# ... SCRIPT HOÀN CHỈNH Ở ĐÂY ...
# Copy TẤT CẢ từ script gốc
# Thêm functions mới vào đúng vị trí
# Giữ nguyên tất cả escape sequences (\\r\\n)
if __name__ == "__main__":
    main()
```
```

**LƯU Ý QUAN TRỌNG:**
- Khi sửa hàm, CHỈ SỬA nếu không có f-strings với escape sequences phức tạp
- Nếu cần sửa logic payload, TẠO HÀM MỚI thay vì sửa hàm cũ
- Giữ code đơn giản - tránh f-strings với \\r\\n trong modifications

🚫 **CÁC HÀM TUYỆT ĐỐI KHÔNG ĐƯỢC SỬA** (do có f-strings phức tạp):
- `build_rce_payload`
- `build_safe_payload`
- `build_vercel_waf_bypass_payload`
- `check_vulnerability` (có nested functions với f-strings)
- `main` (quá phức tạp)
- Bất kỳ hàm nào chứa `\\r\\n` trong strings

✅ **THAY VÀO ĐÓ, TẠO HÀM MỚI:**
- `build_file_read_payload` - payload mới cho đọc file
- `check_vulnerability_with_read_file` - wrapper gọi check_vulnerability với read_file
- `extract_file_content` - trích xuất nội dung file

🔴 **QUAN TRỌNG VỀ MULTIPART PAYLOAD:**
- Khi tạo payload mới TƯƠNG TỰ build_rce_payload, BẮT BUỘC dùng `\\r\\n` KHÔNG PHẢI `\\n`
- COPY CHÍNH XÁC cấu trúc từ hàm build_rce_payload trong script gốc
- Chỉ thay đổi phần command (thay echo bằng cat)
- KHÔNG tự viết multipart body mới, COPY từ hàm có sẵn

---

**SCRIPT GỐC (BẮT BUỘC PHẢI DỰA VÀO SCRIPT NÀY):**
{base_script}

**THÔNG TIN RAG:**
{rag_context}

**YÊU CẦU USER:**
{user_request}

**TARGET:**
{target}

---

🚨 **OUTPUT SCRIPT HOÀN CHỈNH** trong block ```python ... ``` sau dòng "### COMPLETE_SCRIPT:"
🚨 **COPY TẤT CẢ code** từ script gốc, THÊM functions mới vào đúng vị trí
🚨 **GIỮ NGUYÊN \\r\\n** trong tất cả multipart payloads - KHÔNG đổi thành \\n
"""


# ==============================================================================
# MAIN TOOL FUNCTION
# ==============================================================================

@tool
def generate_exploit_script(
    request: str,
    target: str = "",
    base_script_name: str = "",
    rag_context: str = ""
) -> str:
    """
    Tạo hoặc cải tiến script exploit dựa trên yêu cầu user.
    
    Tool này KẾT HỢP:
    - Scripts user đã upload (từ scripts/ folder) - BẮT BUỘC
    - Kiến thức từ RAG (CVE details, payloads, techniques...)
    - Yêu cầu cụ thể của user
    
    AI nên sử dụng tool này khi:
    - User yêu cầu CẢI TIẾN script có sẵn
    - User yêu cầu sửa đổi script để thêm chức năng
    
    Args:
        request (str): Yêu cầu chi tiết của user (ví dụ: "thêm chức năng đọc file")
        target (str): URL/IP mục tiêu
        base_script_name (str): Tên script gốc để cải tiến (ví dụ: "Scanner") - BẮT BUỘC
        rag_context (str): Thông tin bổ sung từ RAG (CVE details, payloads...)
        
    Returns:
        str: Script được cải tiến + validation result
    """
    
    print(f"--- [Script Generator] Request: {request[:100]}... ---")
    print(f"--- [Script Generator] Target: {target} ---")
    print(f"--- [Script Generator] Base script: {base_script_name} ---")
    
    # 1. Load script gốc nếu có
    base_script = ""
    base_script_info = "Không có script gốc. Sẽ tạo mới hoàn toàn."
    
    if base_script_name:
        loaded_script = load_tool_by_name(base_script_name)
        if loaded_script:
            base_script = loaded_script['content']
            base_script_info = f"""
**SCRIPT GỐC: {loaded_script['name']}**
- File: {loaded_script['filename']}
- Loại: {loaded_script['type']}
- Số dòng: {loaded_script['lines']}

```{loaded_script['type']}
{base_script}
```
"""
            print(f"--- [Script Generator] Loaded base script: {loaded_script['name']} ({loaded_script['lines']} lines) ---")
    else:
        # BẮT BUỘC phải có script gốc
        return "❌ **Lỗi:** Bạn phải chỉ định `base_script_name` - tên script gốc để cải tiến. Hãy dùng `list_available_scripts()` để xem danh sách scripts có sẵn."
    
    # 2. Gọi AI để cải tiến script
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "❌ Lỗi: Không tìm thấy GEMINI_API_KEY"
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.3
        )
        
        # Chuẩn bị prompt
        prompt = SCRIPT_GENERATION_PROMPT.format(
            base_script=base_script_info,
            rag_context=rag_context if rag_context else "Không có thông tin RAG bổ sung. Hãy dựa hoàn toàn vào script gốc.",
            user_request=request,
            target=target if target else "Chưa xác định - User sẽ cung cấp khi chạy"
        )
        
        # Gọi AI
        response = llm.invoke(prompt)
        ai_output = response.content if hasattr(response, 'content') else str(response)
        
        print(f"--- [Script Generator] AI Response length: {len(ai_output)} chars ---")
        
        # === LOGIC: Ưu tiên COMPLETE_SCRIPT, fallback to MODIFICATIONS ===
        final_script = ""
        improvement_explanation = ""
        
        # Ưu tiên 1: COMPLETE_SCRIPT (script hoàn chỉnh từ AI)
        if "COMPLETE_SCRIPT:" in ai_output or "### COMPLETE_SCRIPT" in ai_output:
            print("--- [Script Generator] Detected COMPLETE_SCRIPT format ---")
            
            # Tách phần giải thích
            if "## 📝" in ai_output:
                parts = ai_output.split("### COMPLETE_SCRIPT", 1)
                if len(parts) == 2:
                    improvement_explanation = parts[0].strip()
                    script_part = parts[1]
            else:
                script_part = ai_output
            
            # Extract python code block - try multiple patterns
            final_script = ""
            
            # Pattern 1: ```python...```
            code_match = re.search(r'```python\s*(.*?)```', script_part, re.DOTALL)
            if code_match:
                final_script = code_match.group(1).strip()
            
            # Pattern 2: ```...``` (generic code block)
            if not final_script:
                code_match = re.search(r'```\s*(.*?)```', script_part, re.DOTALL)
                if code_match:
                    final_script = code_match.group(1).strip()
            
            # Pattern 3: Look for #!/usr/bin/env python3 marker
            if not final_script and "#!/usr/bin/env python3" in script_part:
                start_idx = script_part.find("#!/usr/bin/env python3")
                # Find the end (next ``` or end of string)
                end_idx = script_part.find("```", start_idx + 1)
                if end_idx == -1:
                    end_idx = len(script_part)
                final_script = script_part[start_idx:end_idx].strip()
            
            # Pattern 4: Fallback to using base_script if AI didn't return complete script
            if not final_script and base_script:
                print("--- [Script Generator] FALLBACK: Using base script as template ---")
                final_script = base_script
            
            if final_script:
                print(f"--- [Script Generator] Extracted complete script: {len(final_script)} chars ---")
            else:
                print("--- [Script Generator] WARNING: No python code block found in COMPLETE_SCRIPT ---")
        
        # Fallback: MODIFICATIONS format (legacy - merge into base script)
        elif base_script and "MODIFICATIONS:" in ai_output:
            # AI trả về dạng modifications → cần merge vào script gốc
            print("--- [Script Generator] Detected MODIFICATIONS format, merging... ---")
            
            # Tách phần giải thích và modifications
            if "## 📝" in ai_output:
                parts = ai_output.split("### MODIFICATIONS:", 1)
                if len(parts) == 2:
                    improvement_explanation = parts[0].strip()
                    modifications_text = parts[1].strip()
                else:
                    modifications_text = ai_output
            else:
                modifications_text = ai_output
            
            # Copy script gốc làm base
            final_script = base_script
            
            # Parse và apply modifications
            # Format: # === SỬA HÀM: function_name === followed by new function code
            
            # Tìm tất cả các modifications
            mod_pattern = r'# === (SỬA HÀM|THÊM HÀM MỚI|ADD|MODIFY): ([^\n=]+) ===\s*\n(.*?)(?=# === |$)'
            modifications = re.findall(mod_pattern, modifications_text, re.DOTALL)
            
            for mod_type, mod_name, mod_code in modifications:
                mod_name = mod_name.strip()
                mod_code = mod_code.strip()
                
                # Loại bỏ markdown code blocks nếu có
                if mod_code.startswith("```"):
                    mod_code = re.sub(r'^```\w*\n?', '', mod_code)
                    mod_code = re.sub(r'\n?```$', '', mod_code)
                
                # === FIX ESCAPE SEQUENCES ===
                # AI có thể output literal \r\n thay vì newline thật
                mod_code = mod_code.replace('\\r\\n', '\n')
                mod_code = mod_code.replace('\\n', '\n')
                mod_code = mod_code.replace('\\t', '    ')  # Convert tab to spaces
                # Fix backslash trong f-strings
                mod_code = mod_code.replace('\\"', '"')
                
                print(f"--- [Script Generator] Applying: {mod_type} - {mod_name} ---")
                
                # Functions that should NOT be modified (too complex, will cause syntax errors)
                SKIP_MODIFY_FUNCTIONS = [
                    'main', 'check_vulnerability', 'build_rce_payload', 
                    'build_safe_payload', 'build_vercel_waf_bypass_payload',
                    'print_result', 'build_response_str', 'build_request_str'
                ]
                
                if "SỬA" in mod_type or "MODIFY" in mod_type:
                    # Tìm và thay thế function trong script gốc
                    # Pattern để tìm function definition
                    func_name = mod_name.split()[0].strip()  # Lấy tên hàm đầu tiên
                    
                    # SKIP complex functions - convert to ADD instead
                    if func_name in SKIP_MODIFY_FUNCTIONS:
                        print(f"    ⚠️ SKIP MODIFY (complex): {func_name} - will ADD as new function instead")
                        # Add as new function with _v2 suffix
                        main_pattern = r'(\ndef main\()'
                        if re.search(main_pattern, final_script):
                            # Rename function to avoid conflict
                            mod_code_renamed = mod_code.replace(f"def {func_name}(", f"def {func_name}_v2(")
                            final_script = re.sub(main_pattern, '\n' + mod_code_renamed + '\n\n\\1', final_script, count=1)
                            print(f"    ✓ Added as new: {func_name}_v2")
                        continue
                    
                    # Tìm function cũ và thay thế
                    old_func_pattern = rf'(def {re.escape(func_name)}\([^)]*\)[^:]*:.*?)(?=\ndef |\nclass |\nif __name__|$)'
                    
                    if re.search(old_func_pattern, final_script, re.DOTALL):
                        final_script = re.sub(old_func_pattern, mod_code + '\n\n', final_script, count=1, flags=re.DOTALL)
                        print(f"    ✓ Replaced function: {func_name}")
                    else:
                        # Không tìm thấy, thêm vào trước main
                        main_pattern = r'(\ndef main\()'
                        if re.search(main_pattern, final_script):
                            final_script = re.sub(main_pattern, '\n' + mod_code + '\n\n\\1', final_script, count=1)
                            print(f"    ✓ Added before main: {func_name}")
                
                elif "THÊM" in mod_type or "ADD" in mod_type:
                    # Thêm function mới trước main()
                    main_pattern = r'(\ndef main\()'
                    if re.search(main_pattern, final_script):
                        final_script = re.sub(main_pattern, '\n' + mod_code + '\n\n\\1', final_script, count=1)
                    else:
                        # Thêm vào cuối file trước if __name__
                        name_main_pattern = r'(\nif __name__)'
                        if re.search(name_main_pattern, final_script):
                            final_script = re.sub(name_main_pattern, '\n' + mod_code + '\n\\1', final_script, count=1)
                        else:
                            final_script += '\n\n' + mod_code
                    print(f"    ✓ Added new function/code")
            
            # Nếu không parse được modifications, giữ nguyên output AI
            if not modifications:
                print("--- [Script Generator] No parseable modifications, using AI output as-is ---")
                final_script = ai_output
        
        else:
            # AI trả về script hoàn chỉnh (script ngắn hoặc tạo mới)
            print("--- [Script Generator] Full script output ---")
            
            if "## 📝" in ai_output:
                parts = ai_output.split("---", 1)
                if len(parts) == 2:
                    improvement_explanation = parts[0].strip()
                    final_script = parts[1].strip()
                else:
                    final_script = ai_output
            else:
                final_script = ai_output
            
            # Clean up - lấy phần code từ response
            if "```python" in final_script:
                match = re.search(r'```python\n(.*?)```', final_script, re.DOTALL)
                if match:
                    final_script = match.group(1).strip()
            elif "```bash" in final_script:
                match = re.search(r'```bash\n(.*?)```', final_script, re.DOTALL)
                if match:
                    final_script = match.group(1).strip()
            
            # Nếu script bắt đầu bằng shebang nhưng không được extract đúng
            if not final_script.startswith("#!") and "#!/" in final_script:
                match = re.search(r'(#!/.*)', final_script, re.DOTALL)
                if match:
                    final_script = match.group(1).strip()
        
        # Gán lại cho generated_script để code sau dùng
        generated_script = final_script
        
        # 4. Validate script VỚI AUTO-FIX LOOP
        script_type = "bash" if generated_script.startswith("#!/bin/bash") else "python"
        validation = validate_script(generated_script, script_type)
        
        # === NEW: Check for truncated script ===
        from utils.script_validator import is_script_truncated
        is_truncated, truncation_info = is_script_truncated(generated_script)
        
        if is_truncated:
            print(f"--- [Script Generator] DETECTED TRUNCATED SCRIPT: {truncation_info[:50]}... ---")
            
            # Try to continue generating the missing part
            MAX_CONTINUATION_TRIES = 2
            for cont_try in range(1, MAX_CONTINUATION_TRIES + 1):
                print(f"--- [Script Generator] Continuation attempt {cont_try}/{MAX_CONTINUATION_TRIES}... ---")
                
                # Get last 100 lines for context
                lines = generated_script.split('\n')
                last_100_lines = '\n'.join(lines[-100:]) if len(lines) > 100 else generated_script
                
                continuation_prompt = f"""Script Python sau đây bị CẮT NGẮN, cần hoàn thành phần còn lại.

**100 DÒNG CUỐI của script (để tiếp tục):**
```python
{last_100_lines}
```

**VẤN ĐỀ:** Script bị cắt ngắn tại: `{truncation_info}`

**YÊU CẦU:**
1. TIẾP TỤC viết từ dòng cuối cùng
2. Hoàn thành phần argparse/main() còn thiếu
3. Thêm `if __name__ == "__main__": main()` ở cuối
4. KHÔNG lặp lại code đã có

**CHỈ TRẢ VỀ PHẦN CÒN THIẾU** trong block ```python ... ```"""

                try:
                    cont_response = llm.invoke(continuation_prompt)
                    cont_output = cont_response.content if hasattr(cont_response, 'content') else str(cont_response)
                    
                    # Extract continuation code
                    cont_code = ""
                    if "```python" in cont_output:
                        match = re.search(r'```python\n(.*?)```', cont_output, re.DOTALL)
                        if match:
                            cont_code = match.group(1).strip()
                    elif "```" in cont_output:
                        match = re.search(r'```\n?(.*?)```', cont_output, re.DOTALL)
                        if match:
                            cont_code = match.group(1).strip()
                    
                    if cont_code:
                        # Merge: append continuation to existing script
                        # Remove redundant first line if it's incomplete from original
                        if truncation_info and truncation_info.endswith('.'):
                            # Script ended with something like "parser." - remove that incomplete line
                            lines = generated_script.split('\n')
                            if lines and lines[-1].strip().endswith('.'):
                                lines = lines[:-1]
                            generated_script = '\n'.join(lines)
                        
                        generated_script = generated_script.rstrip() + '\n' + cont_code
                        print(f"--- [Script Generator] Continuation added: {len(cont_code)} chars ---")
                        
                        # Re-validate
                        validation = validate_script(generated_script, script_type)
                        is_truncated, truncation_info = is_script_truncated(generated_script)
                        
                        if validation.is_valid and not is_truncated:
                            print(f"--- [Script Generator] Continuation SUCCESS! ---")
                            break
                        else:
                            print(f"--- [Script Generator] Still invalid after continuation ---")
                    
                except Exception as cont_error:
                    print(f"--- [Script Generator] Continuation error: {cont_error} ---")
        
        MAX_FIX_RETRIES = 3
        fix_attempt = 0
        
        while not validation.is_valid and fix_attempt < MAX_FIX_RETRIES:
            fix_attempt += 1
            print(f"--- [Script Generator] Validation FAILED, auto-fixing (attempt {fix_attempt}/{MAX_FIX_RETRIES})... ---")
            
            # Tạo prompt để AI tự fix lỗi - bao gồm context từ script gốc
            # Trích xuất một phần base script để AI học pattern đúng
            base_script_snippet = ""
            if base_script:
                # Lấy function build_rce_payload làm reference
                match = re.search(r'(def build_rce_payload.*?(?=\ndef |\nclass |\Z))', base_script, re.DOTALL)
                if match:
                    base_script_snippet = f"""
**THAM KHẢO - Function từ script gốc (pattern đúng):**
```python
{match.group(1)[:1500]}
```
Lưu ý: Trong script gốc, multipart payloads dùng `\\r\\n` (carriage return + newline).
"""

            fix_prompt = f"""Script có lỗi cú pháp. Hãy phân tích lỗi, so sánh với pattern trong script gốc, và sửa cho đúng.

**LỖI ĐÃ PHÁT HIỆN:**
{chr(10).join(validation.errors)}

{base_script_snippet}

**SCRIPT CẦN SỬA:**
```python
{generated_script}
```

**HƯỚNG DẪN SỬA:**
1. Phân tích lỗi - hiểu TẠI SAO nó xảy ra
2. So sánh với pattern trong script gốc ở trên
3. Sửa tất cả lỗi cú pháp
4. Trả về script Python hoàn chỉnh đã sửa
5. KHÔNG giải thích, CHỈ trả về code trong block ```python ... ```
"""
            
            try:
                fix_response = llm.invoke(fix_prompt)
                fix_output = fix_response.content if hasattr(fix_response, 'content') else str(fix_response)
                
                # Extract code từ response
                if "```python" in fix_output:
                    match = re.search(r'```python\n(.*?)```', fix_output, re.DOTALL)
                    if match:
                        generated_script = match.group(1).strip()
                elif "```" in fix_output:
                    match = re.search(r'```\n?(.*?)```', fix_output, re.DOTALL)
                    if match:
                        generated_script = match.group(1).strip()
                else:
                    generated_script = fix_output.strip()
                
                # Validate lại
                validation = validate_script(generated_script, script_type)
                if validation.is_valid:
                    print(f"--- [Script Generator] After fix attempt {fix_attempt}: PASS ---")
                else:
                    print(f"--- [Script Generator] After fix attempt {fix_attempt}: FAIL ---")
                    for err in validation.errors[:3]:  # Show first 3 errors
                        print(f"    ❌ {err}")
                
            except Exception as fix_error:
                print(f"--- [Script Generator] Fix attempt {fix_attempt} error: {fix_error} ---")
                break
        
        validation_text = format_validation_result(validation)
        
        print(f"--- [Script Generator] Script generated ({len(generated_script.split(chr(10)))} lines) ---")
        print(f"--- [Script Generator] Final Validation: {'PASS' if validation.is_valid else 'FAIL'} ---")
        
        # 5. Trả về kết quả
        # Truncate script cho hiển thị
        script_lines = generated_script.split('\n')
        if len(script_lines) > 50:
            display_script = '\n'.join(script_lines[:50]) + f"\n\n# ... [{len(script_lines) - 50} dòng còn lại] ..."
        else:
            display_script = generated_script
        
        # Tạo phần hiển thị cải tiến
        improvement_section = ""
        if improvement_explanation:
            improvement_section = f"""
### 📝 Điểm Cải Tiến So Với Script Gốc:

{improvement_explanation}

---
"""
        
        # === TỰ ĐỘNG LƯU SCRIPT CẢI TIẾN THÀNH FILE MỚI ===
        # CHỈ lưu khi script hoàn chỉnh và chạy được
        saved_file_info = ""
        saved_script_name = ""
        if validation.is_valid and base_script_name:
            try:
                # Tạo tên file mới với version
                scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scripts')
                base_filename = base_script_name.lower()
                
                # Tìm version tiếp theo
                version = 2
                while os.path.exists(os.path.join(scripts_dir, f"{base_filename}_v{version}.py")):
                    version += 1
                
                new_filename = f"{base_filename}_v{version}.py"
                new_filepath = os.path.join(scripts_dir, new_filename)
                
                # Tên script để agent sử dụng (e.g., "Scanner V2")
                saved_script_name = f"{base_script_name} V{version}"
                
                # Lưu file
                with open(new_filepath, 'w', encoding='utf-8') as f:
                    f.write(generated_script)
                
                # === POST-SAVE VALIDATION ===
                # Đọc lại file đã lưu và validate
                with open(new_filepath, 'r', encoding='utf-8') as f:
                    saved_content = f.read()
                
                # Kiểm tra script có bị cắt không
                if len(saved_content) < len(generated_script) * 0.95:  # Cho phép 5% sai số
                    print(f"--- [Script Generator] WARNING: Saved file may be truncated! ---")
                    print(f"    Original: {len(generated_script)} chars, Saved: {len(saved_content)} chars")
                    saved_file_info = f"\n\n⚠️ Script có thể bị cắt khi lưu. Hãy kiểm tra lại."
                else:
                    # Validate lại file đã lưu
                    post_validation = validate_script(saved_content, script_type)
                    if not post_validation.is_valid:
                        print(f"--- [Script Generator] WARNING: Saved file has syntax errors! ---")
                        for err in post_validation.errors[:3]:
                            print(f"    ❌ {err}")
                        saved_file_info = f"\n\n⚠️ File đã lưu nhưng có lỗi syntax. Vui lòng sửa lại."
                    else:
                        saved_file_info = f"\n\n💾 **Đã lưu thành:** `scripts/{new_filename}` (Tên script: `{saved_script_name}`)"
                
                print(f"--- [Script Generator] Saved to: {new_filepath} ---")
                print(f"--- [Script Generator] Script name for running: {saved_script_name} ---")
                
            except Exception as save_err:
                print(f"--- [Script Generator] Save error: {save_err} ---")
                saved_file_info = f"\n\n⚠️ Không thể lưu file: {save_err}"
        
        args_value = f"-u {target}" if target else ""
        result = f"""__SCRIPT_PROPOSAL__
{{
    "type": "{script_type}",
    "description": "{request[:100]}",
    "target": "{target}",
    "args": "{args_value}",
    "saved_script_name": "{saved_script_name}",
    "script": {repr(generated_script)}
}}
__END_SCRIPT_PROPOSAL__

## 🔧 Script {"Được Cải Tiến" if base_script_name else "Được Tạo"} ({script_type.upper()})

**Yêu cầu:** {request}
**Mục tiêu:** {target if target else "Chưa xác định"}
**Nguồn tham khảo:** {base_script_name if base_script_name else "Template"} + AI Generation
**Độ dài:** {len(script_lines)} dòng{saved_file_info}
**▶️ Để chạy script này:** Gõ "chạy {saved_script_name}" hoặc bấm xác nhận bên dưới
{improvement_section}
### Validation Result:
{validation_text}

### Script Preview:
```{script_type}
{display_script}
```

{"⚠️ **Xác nhận:** Bạn có muốn chạy script này trên Kali Linux không? (Trả lời 'có')" if validation.is_valid else "❌ Script có lỗi, vui lòng yêu cầu sửa lại."}
"""
        
        return result
        
    except Exception as e:
        print(f"--- [Script Generator] Error: {e} ---")
        return f"❌ Lỗi khi tạo script: {str(e)}"


@tool
def list_available_scripts() -> str:
    """
    Liệt kê tất cả scripts có sẵn trong hệ thống.
    
    Scripts user đã upload nằm trong folder scripts/
    
    Returns:
        str: Danh sách scripts có sẵn
    """
    
    # Scripts từ folder
    tools = get_available_tools()
    
    if tools:
        scripts_info = "## 📁 Scripts có sẵn (scripts/ folder):\n\n"
        for t in tools:
            scripts_info += f"- **{t['name']}** (`{t['filename']}`)\n"
            if t['description']:
                scripts_info += f"  _{t['description'][:100]}..._\n"
        
        scripts_info += "\n**💡 Hướng dẫn:** Dùng `generate_exploit_script(base_script_name=\"<tên script>\", request=\"<yêu cầu>\")` để cải tiến script."
    else:
        scripts_info = "## 📁 Scripts có sẵn:\n\n_Chưa có script nào. Upload qua UI (trang Setup) để thêm._\n"
    
    return scripts_info


# ==============================================================================
# TEST
# ==============================================================================

if __name__ == "__main__":
    # Test list_available_scripts
    print(list_available_scripts.invoke({}))
    
    # Test generate_exploit_script
    result = generate_exploit_script.invoke({
        "request": "Thêm chức năng đọc file /etc/passwd",
        "target": "http://example.com",
        "base_script_name": "scanner"
    })
    print(result)
