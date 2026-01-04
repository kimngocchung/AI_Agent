# File: utils/tool_loader.py
# Module để load scripts từ folder scripts/ (không qua RAG chunking)
# User có thể upload scripts vào đây để AI đọc và sử dụng

import os
import re
from typing import Optional, Dict, List

# Path đến folder chứa user scripts
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")


def get_available_tools() -> List[Dict]:
    """
    Liệt kê tất cả các tool có sẵn trong folder tools/
    Returns: List các dict với name, path, description
    """
    tools = []
    
    if not os.path.exists(SCRIPTS_DIR):
        os.makedirs(SCRIPTS_DIR, exist_ok=True)
        return tools
    
    for filename in os.listdir(SCRIPTS_DIR):
        if filename.endswith(('.py', '.sh', '.bash')):
            filepath = os.path.join(SCRIPTS_DIR, filename)
            
            # Đọc description từ docstring nếu có
            description = ""
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Tìm docstring đầu tiên
                    match = re.search(r'"""(.*?)"""', content, re.DOTALL)
                    if match:
                        description = match.group(1).strip()[:200]
            except:
                pass
            
            tools.append({
                "name": filename.replace('.py', '').replace('.sh', '').replace('_', ' ').title(),
                "filename": filename,
                "path": filepath,
                "description": description
            })
    
    return tools


def load_tool_by_name(tool_name: str) -> Optional[Dict]:
    """
    Load nội dung script theo tên tool.
    Hỗ trợ tìm fuzzy (ví dụ: "script scanner" → "script_scanner.py")
    ƯU TIÊN: Exact match > Contains match > Fuzzy match
    
    Returns: Dict với name, content, type (python/bash), path
    """
    if not os.path.exists(SCRIPTS_DIR):
        return None
    
    # Normalize tên tool để tìm kiếm
    normalized_name = tool_name.lower().strip()
    normalized_name = re.sub(r'[^a-z0-9]', '', normalized_name)  # Bỏ ký tự đặc biệt
    
    candidates = []
    
    for filename in os.listdir(SCRIPTS_DIR):
        if not filename.endswith(('.py', '.sh', '.bash')):
            continue
        
        # Normalize tên file để so sánh
        file_base = filename.rsplit('.', 1)[0]
        normalized_file = re.sub(r'[^a-z0-9]', '', file_base.lower())
        
        # Tính điểm ưu tiên
        # Priority 1: Exact match (cao nhất)
        if normalized_name == normalized_file:
            priority = 1
        # Priority 2: Query chứa đầy đủ tên file
        elif normalized_file in normalized_name:
            priority = 2
        # Priority 3: Tên file chứa query
        elif normalized_name in normalized_file:
            priority = 3
        else:
            continue
        
        candidates.append((priority, len(normalized_file), filename, file_base))
    
    if not candidates:
        return None
    
    # Sort: priority thấp nhất (exact match) trước, sau đó dài nhất (cụ thể nhất)
    candidates.sort(key=lambda x: (x[0], -x[1]))
    
    # Lấy candidate tốt nhất
    _, _, filename, file_base = candidates[0]
    filepath = os.path.join(SCRIPTS_DIR, filename)
    
    print(f"--- [Tool Loader] Selected: {filename} (from {len(candidates)} candidates) ---")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Xác định loại script
        script_type = "bash" if filename.endswith(('.sh', '.bash')) else "python"
        
        return {
            "name": file_base.replace('_', ' ').title(),
            "filename": filename,
            "path": filepath,
            "content": content,
            "type": script_type,
            "lines": len(content.split('\n'))
        }
    except Exception as e:
        print(f"[Tool Loader] Error loading {filename}: {e}")
        return None


def detect_tool_request(query: str) -> Optional[str]:
    """
    Phát hiện xem user có đang yêu cầu dùng một tool cụ thể không.
    ƯU TIÊN: Exact match > Contains match > Partial match
    
    Returns: Tên tool nếu phát hiện, None nếu không
    """
    # Các từ khóa cho thấy user muốn dùng tool
    use_keywords = ["dùng", "chạy", "sử dụng", "scan bằng", "kiểm tra bằng", 
                    "cải tiến", "modify", "improve", "dựa trên", "based on",
                    "script", "tool", "scanner"]
    
    query_lower = query.lower()
    
    # Kiểm tra xem có từ khóa dùng tool không
    has_use_keyword = any(kw in query_lower for kw in use_keywords)
    
    if not has_use_keyword:
        return None
    
    # Lấy danh sách tools có sẵn
    tools = get_available_tools()
    
    print(f"--- [Tool Loader] Available tools: {[t['name'] for t in tools]} ---")
    print(f"--- [Tool Loader] Query: {query_lower[:100]} ---")
    
    # Chuẩn hóa query
    normalized_query = re.sub(r'[^a-z0-9]', '', query_lower)
    
    candidates = []
    
    for tool in tools:
        tool_name_lower = tool["name"].lower()
        filename_base = tool["filename"].replace('.py', '').replace('.sh', '').replace('_', '').lower()
        
        # Normalize cả tên tool
        normalized_tool = re.sub(r'[^a-z0-9]', '', tool_name_lower)
        
        # Tính priority (số nhỏ = ưu tiên cao)
        priority = 999
        
        # Priority 1: Exact match với filename (cao nhất)
        if filename_base in normalized_query or normalized_tool in normalized_query:
            # Ưu tiên tên dài hơn (cụ thể hơn)
            priority = 100 - len(filename_base)
        
        # Priority 2: Query chứa tên tool
        elif tool_name_lower in query_lower:
            priority = 200 - len(tool_name_lower)
        
        # Priority 3: Partial match
        else:
            query_words = set(normalized_query.split())
            tool_words = set(tool_name_lower.split())
            if tool_words & query_words:
                priority = 300
        
        if priority < 999:
            candidates.append((priority, len(filename_base), tool))
    
    if not candidates:
        print(f"--- [Tool Loader] No tool match found ---")
        return None
    
    # Sort: priority thấp nhất trước, sau đó dài nhất (cụ thể nhất)
    candidates.sort(key=lambda x: (x[0], -x[1]))
    
    selected = candidates[0][2]
    print(f"--- [Tool Loader] Selected: {selected['name']} (from {len(candidates)} candidates) ---")
    
    return selected["name"]


def get_tool_context(query: str) -> str:
    """
    Nếu query yêu cầu một tool cụ thể, load và trả về context đầy đủ của tool đó.
    
    Returns: String chứa nội dung tool hoặc empty string nếu không tìm thấy
    """
    tool_name = detect_tool_request(query)
    
    if not tool_name:
        return ""
    
    tool = load_tool_by_name(tool_name)
    
    if not tool:
        return ""
    
    print(f"--- [Tool Loader] Loaded tool: {tool['name']} ({tool['lines']} lines) ---")
    
    # Truncate script cho context (để AI xử lý nhanh hơn)
    # Nhưng vẫn giữ script đầy đủ trong tool dict
    script_lines = tool['content'].split('\n')
    if len(script_lines) > 100:
        truncated_content = '\n'.join(script_lines[:100]) + f"\n\n# ... [{len(script_lines) - 100} dòng còn lại - Script đầy đủ sẽ được dùng khi thực thi] ..."
    else:
        truncated_content = tool['content']
    
    context = f"""
📁 **TOOL CÓ SẴN TRONG HỆ THỐNG: {tool['name']}**

**Loại:** {tool['type'].upper()}
**File:** {tool['filename']}
**Số dòng:** {tool['lines']}
**Đường dẫn:** {tool['path']}

**PREVIEW SCRIPT (100 dòng đầu - Script đầy đủ sẽ dùng khi thực thi):**

```{tool['type']}
{truncated_content}
```

⚠️ **HÀNH ĐỘNG BẮT BUỘC:** 
Khi user yêu cầu DÙNG script này → Gọi ngay:
```
propose_exploit_script(
    script_content=FULL_SCRIPT_FROM_FILE,  # Lấy từ file path ở trên
    script_type="{tool['type']}",
    description="Chạy {tool['name']}",
    target="<URL từ user>"
)
```

QUAN TRỌNG: Hệ thống sẽ tự load TOÀN BỘ script từ file khi thực thi. Bạn chỉ cần gọi tool với tham số đúng.
"""
    
    return context


# Test
if __name__ == "__main__":
    print("Available tools:", get_available_tools())
    print("\nDetect 'dùng script scanner':", detect_tool_request("dùng script scanner để quét"))
