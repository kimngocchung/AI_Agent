# File: core/tools/code_review_tool.py
"""
Static Code Analysis Tool - LUỒNG 4
Cho phép AI Agent đọc và phân tích source code để tìm lỗ hổng bảo mật

Tools bao gồm:
1. scan_directory_for_code: Liệt kê files code trong thư mục
2. read_source_file: Đọc nội dung file source code
3. scan_hardcoded_credentials: Tìm passwords, API keys, secrets
4. scan_idor_vulnerabilities: Phát hiện IDOR patterns
5. scan_xss_vulnerabilities: Tìm XSS vulnerabilities
6. analyze_security_config: Phân tích cấu hình bảo mật
"""

import os
import re
from typing import List, Dict, Optional
from langchain_core.tools import tool
from pathlib import Path

# Các extensions được hỗ trợ
SUPPORTED_EXTENSIONS = {
    'java': ['.java'],
    'javascript': ['.js', '.jsx', '.ts', '.tsx'],
    'python': ['.py'],
    'config': ['.yml', '.yaml', '.json', '.xml', '.properties', '.env'],
    'web': ['.html', '.htm', '.php'],
}

ALL_EXTENSIONS = [ext for exts in SUPPORTED_EXTENSIONS.values() for ext in exts]


def get_all_files(directory: str, extensions: List[str] = None, max_files: int = 100) -> List[str]:
    """
    Lấy danh sách tất cả files với extensions cho trước trong thư mục (đệ quy)
    """
    if extensions is None:
        extensions = ALL_EXTENSIONS
    
    files = []
    try:
        for root, dirs, filenames in os.walk(directory):
            # Skip hidden directories và node_modules, target, build
            dirs[:] = [d for d in dirs if not d.startswith('.') 
                      and d not in ['node_modules', 'target', 'build', 'dist', '__pycache__', '.git']]
            
            for filename in filenames:
                if any(filename.endswith(ext) for ext in extensions):
                    files.append(os.path.join(root, filename))
                    
                    if len(files) >= max_files:
                        return files
    except Exception as e:
        print(f"[Code Review] Error scanning directory: {e}")
    
    return files


@tool
def scan_directory_for_code(directory_path: str, file_type: str = "all") -> str:
    """
    Quét thư mục và liệt kê các file source code.
    
    Args:
        directory_path: Đường dẫn tuyệt đối đến thư mục cần quét
        file_type: Loại file cần tìm: "java", "javascript", "python", "config", "web", hoặc "all"
        
    Returns:
        Danh sách các file tìm thấy với đường dẫn
    """
    print(f"--- [Code Review] Scanning directory: {directory_path} ---")
    
    if not os.path.exists(directory_path):
        return f"❌ Thư mục không tồn tại: {directory_path}"
    
    if not os.path.isdir(directory_path):
        return f"❌ Đường dẫn không phải là thư mục: {directory_path}"
    
    # Xác định extensions cần tìm
    if file_type == "all":
        extensions = ALL_EXTENSIONS
    elif file_type in SUPPORTED_EXTENSIONS:
        extensions = SUPPORTED_EXTENSIONS[file_type]
    else:
        extensions = ALL_EXTENSIONS
    
    files = get_all_files(directory_path, extensions)
    
    if not files:
        return f"Không tìm thấy file {file_type} nào trong {directory_path}"
    
    # Format output
    result = f"## 📁 Kết quả quét thư mục\n\n"
    result += f"**Thư mục:** `{directory_path}`\n"
    result += f"**Loại file:** {file_type}\n"
    result += f"**Số file tìm thấy:** {len(files)}\n\n"
    result += "### Danh sách files:\n\n"
    
    # Group by extension
    by_ext = {}
    for f in files:
        ext = os.path.splitext(f)[1]
        if ext not in by_ext:
            by_ext[ext] = []
        by_ext[ext].append(f)
    
    for ext, file_list in sorted(by_ext.items()):
        result += f"**{ext}** ({len(file_list)} files):\n"
        for f in file_list[:20]:  # Limit to 20 per extension
            rel_path = os.path.relpath(f, directory_path)
            result += f"- `{rel_path}`\n"
        if len(file_list) > 20:
            result += f"- ... và {len(file_list) - 20} files khác\n"
        result += "\n"
    
    return result


@tool
def read_source_file(file_path: str, start_line: int = 1, end_line: int = 500) -> str:
    """
    Đọc nội dung của file source code.
    
    Args:
        file_path: Đường dẫn tuyệt đối đến file cần đọc
        start_line: Dòng bắt đầu (mặc định 1)
        end_line: Dòng kết thúc (mặc định 500)
        
    Returns:
        Nội dung file với số dòng
    """
    print(f"--- [Code Review] Reading file: {file_path} ---")
    
    if not os.path.exists(file_path):
        return f"❌ File không tồn tại: {file_path}"
    
    if not os.path.isfile(file_path):
        return f"❌ Đường dẫn không phải là file: {file_path}"
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Adjust line numbers
        start_line = max(1, start_line)
        end_line = min(total_lines, end_line)
        
        selected_lines = lines[start_line-1:end_line]
        
        result = f"## 📄 File: `{os.path.basename(file_path)}`\n\n"
        result += f"**Đường dẫn:** `{file_path}`\n"
        result += f"**Tổng số dòng:** {total_lines}\n"
        result += f"**Hiển thị:** dòng {start_line} - {end_line}\n\n"
        
        # Detect language for syntax highlighting
        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {
            '.java': 'java', '.py': 'python', '.js': 'javascript',
            '.ts': 'typescript', '.tsx': 'tsx', '.jsx': 'jsx',
            '.yml': 'yaml', '.yaml': 'yaml', '.json': 'json',
            '.xml': 'xml', '.html': 'html', '.css': 'css'
        }
        lang = lang_map.get(ext, '')
        
        result += f"```{lang}\n"
        for i, line in enumerate(selected_lines, start=start_line):
            result += f"{i:4d}: {line}"
        result += "```\n"
        
        return result
        
    except Exception as e:
        return f"❌ Lỗi đọc file: {str(e)}"


@tool
def scan_hardcoded_credentials(directory_path: str, file_types: str = "all") -> str:
    """
    Quét thư mục tìm hardcoded credentials (passwords, API keys, secrets).
    
    Args:
        directory_path: Đường dẫn đến thư mục cần quét
        file_types: "all", "java", "python", "javascript", "config"
        
    Returns:
        Danh sách các credentials tìm thấy với vị trí
    """
    print(f"--- [Code Review] Scanning for hardcoded credentials in: {directory_path} ---")
    
    if not os.path.exists(directory_path):
        return f"❌ Thư mục không tồn tại: {directory_path}"
    
    # Patterns để tìm credentials
    patterns = {
        'password': [
            r'password\s*[=:]\s*["\']([^"\']{3,})["\']',
            r'passwd\s*[=:]\s*["\']([^"\']{3,})["\']',
            r'pwd\s*[=:]\s*["\']([^"\']{3,})["\']',
            r'PASS\s*[=:]\s*["\']([^"\']{3,})["\']',
        ],
        'api_key': [
            r'api[_-]?key\s*[=:]\s*["\']([^"\']{10,})["\']',
            r'apikey\s*[=:]\s*["\']([^"\']{10,})["\']',
            r'API_KEY\s*[=:]\s*["\']([^"\']{10,})["\']',
            r'access[_-]?key\s*[=:]\s*["\']([^"\']{10,})["\']',
        ],
        'secret': [
            r'secret\s*[=:]\s*["\']([^"\']{8,})["\']',
            r'SECRET\s*[=:]\s*["\']([^"\']{8,})["\']',
            r'secret[_-]?key\s*[=:]\s*["\']([^"\']{8,})["\']',
            r'private[_-]?key\s*[=:]\s*["\']([^"\']{10,})["\']',
        ],
        'token': [
            r'token\s*[=:]\s*["\']([^"\']{10,})["\']',
            r'TOKEN\s*[=:]\s*["\']([^"\']{10,})["\']',
            r'auth[_-]?token\s*[=:]\s*["\']([^"\']{10,})["\']',
            r'bearer\s+([a-zA-Z0-9_-]{20,})',
        ],
        'connection_string': [
            r'mongodb(\+srv)?://[^\s"\']+',
            r'mysql://[^\s"\']+',
            r'postgresql://[^\s"\']+',
            r'redis://[^\s"\']+',
        ],
        'aws': [
            r'AKIA[A-Z0-9]{16}',  # AWS Access Key ID
            r'aws[_-]?access[_-]?key\s*[=:]\s*["\']([^"\']{16,})["\']',
            r'aws[_-]?secret\s*[=:]\s*["\']([^"\']{30,})["\']',
        ],
    }
    
    # Get files to scan
    if file_types == "all":
        extensions = ALL_EXTENSIONS
    elif file_types in SUPPORTED_EXTENSIONS:
        extensions = SUPPORTED_EXTENSIONS[file_types]
    else:
        extensions = ALL_EXTENSIONS
    
    files = get_all_files(directory_path, extensions, max_files=200)
    
    findings = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            for cred_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        # Find line number
                        pos = match.start()
                        line_num = content[:pos].count('\n') + 1
                        
                        # Get the matched line
                        if line_num <= len(lines):
                            matched_line = lines[line_num - 1].strip()
                        else:
                            matched_line = match.group(0)
                        
                        findings.append({
                            'type': cred_type,
                            'file': os.path.relpath(file_path, directory_path),
                            'line': line_num,
                            'match': match.group(0)[:100],
                            'context': matched_line[:150]
                        })
        except Exception as e:
            continue
    
    # Format output
    result = f"## 🔐 Scan Hardcoded Credentials\n\n"
    result += f"**Thư mục:** `{directory_path}`\n"
    result += f"**Files đã quét:** {len(files)}\n"
    result += f"**Findings:** {len(findings)}\n\n"
    
    if not findings:
        result += "✅ Không tìm thấy hardcoded credentials nào!\n"
        return result
    
    result += "### ⚠️ Credentials Tìm Thấy:\n\n"
    
    # Group by type
    by_type = {}
    for f in findings:
        if f['type'] not in by_type:
            by_type[f['type']] = []
        by_type[f['type']].append(f)
    
    for cred_type, items in by_type.items():
        result += f"#### 🔑 {cred_type.upper()} ({len(items)} findings)\n\n"
        for item in items[:10]:  # Limit output
            result += f"- **File:** `{item['file']}` (line {item['line']})\n"
            result += f"  ```\n  {item['context']}\n  ```\n\n"
        if len(items) > 10:
            result += f"- ... và {len(items) - 10} findings khác\n\n"
    
    result += "\n### 🛠️ Khuyến Nghị:\n"
    result += "1. Di chuyển tất cả credentials sang environment variables\n"
    result += "2. Sử dụng secrets management (HashiCorp Vault, AWS Secrets Manager)\n"
    result += "3. Thêm các files chứa secrets vào .gitignore\n"
    result += "4. Rotate tất cả credentials đã bị leak\n"
    
    return result


@tool
def scan_idor_vulnerabilities(directory_path: str) -> str:
    """
    Quét thư mục tìm IDOR vulnerabilities (Insecure Direct Object Reference).
    Tìm các patterns: findById, getById mà không có kiểm tra ownership.
    
    Args:
        directory_path: Đường dẫn đến thư mục chứa source code
        
    Returns:
        Danh sách các potential IDOR vulnerabilities
    """
    print(f"--- [Code Review] Scanning for IDOR vulnerabilities in: {directory_path} ---")
    
    if not os.path.exists(directory_path):
        return f"❌ Thư mục không tồn tại: {directory_path}"
    
    # IDOR patterns to look for - MỞ RỘNG để phát hiện nhiều hơn
    dangerous_patterns = [
        # === Java/Spring patterns ===
        # findById với bất kỳ tham số nào
        (r'\.findById\s*\([^)]+\)', 'findById() - potential IDOR'),
        (r'\.getById\s*\([^)]+\)', 'getById() - potential IDOR'),
        (r'\.findOne\s*\([^)]+\)', 'findOne() - potential IDOR'),
        (r'repository\.[a-zA-Z]*[Bb]y[Ii]d\s*\(', 'Repository.*ById() method'),
        
        # @PathVariable với bất kỳ variable name nào (orderId, userId, bookId, etc.)
        (r'@PathVariable[^)]*\)\s*\w+\s+\w*[Ii]d', '@PathVariable with ID parameter'),
        (r'@PathVariable\s*\(\s*["\'][^"\']+["\']\s*\)', '@PathVariable with named param'),
        (r'@PathVariable\s+\w+\s+\w+', '@PathVariable parameter'),
        
        # @RequestParam với id
        (r'@RequestParam[^)]*[Ii]d', '@RequestParam with ID'),
        
        # Direct object reference trong Controller
        (r'Service\.[a-zA-Z]*[Bb]y[Ii]d\s*\(', 'Service.*ById() call'),
        (r'getOrder\s*\([^)]*\)', 'getOrder() - check authorization'),
        (r'getUser\s*\([^)]*\)', 'getUser() - check authorization'),
        (r'getAccount\s*\([^)]*\)', 'getAccount() - check authorization'),
        (r'getAddress\s*\([^)]*\)', 'getAddress() - check authorization'),
        
        # === Node.js/Express patterns ===
        (r'req\.params\.[a-zA-Z]*[Ii]d', 'req.params.id without validation'),
        (r'req\.query\.[a-zA-Z]*[Ii]d', 'req.query.id without validation'),
        (r'findOne\s*\(\s*\{[^}]*_id', 'MongoDB findOne by _id'),
        (r'findById\s*\(req\.', 'findById from request param'),
        
        # === Python/Django/Flask patterns ===
        (r'get_object_or_404\s*\([^,]+,\s*(pk|id)=', 'get_object_or_404 without ownership'),
        (r'\.objects\.get\s*\(\s*(pk|id)=', 'Django objects.get()'),
        (r'\.objects\.filter\s*\(\s*(pk|id)=', 'Django objects.filter() by id'),
    ]
    
    # Good patterns (ownership checks) - Nếu có thì skip
    good_patterns = [
        r'getCurrentUser',
        r'currentUser\.',
        r'getAuthenticatedUser',
        r'\.getUserId\s*\(\s*\)',
        r'\.getAccountId\s*\(\s*\)',
        r'request\.user',
        r'req\.user',
        r'session\.user',
        r'@PreAuthorize',
        r'@Secured',
        r'@RolesAllowed',
        r'hasPermission',
        r'hasAuthority',
        r'isOwner',
        r'checkOwnership',
        r'verifyOwnership',
        r'belongsTo',
        r'\.equals\s*\(\s*userId',
        r'\.equals\s*\(\s*currentUser',
        r'accountId\.equals',
        r'userId\.equals',
    ]
    
    # Get Java and JS/TS files (most common for APIs)
    extensions = ['.java', '.js', '.ts', '.py']
    files = get_all_files(directory_path, extensions, max_files=200)
    
    findings = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Skip test files
            if 'test' in file_path.lower() or 'spec' in file_path.lower():
                continue
            
            for pattern, desc in dangerous_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    pos = match.start()
                    line_num = content[:pos].count('\n') + 1
                    
                    # CHỈ CHECK 2 DÒNG TRƯỚC VÀ SAU (không phải 5 dòng)
                    # Vì ownership check phải gần trực tiếp với findById
                    start_line = max(0, line_num - 3)
                    end_line = min(len(lines), line_num + 2)
                    context = '\n'.join(lines[start_line:end_line])
                    
                    # Check if there's an ownership check TRỰC TIẾP nearby
                    has_ownership_check = any(
                        re.search(good_pattern, context, re.IGNORECASE) 
                        for good_pattern in good_patterns
                    )
                    
                    # LUÔN BÁO CÁO nhưng với severity khác nhau
                    # - Không có ownership check = HIGH
                    # - Có ownership check gần = MEDIUM (vẫn cần review)
                    # - Controller/API endpoint = HIGH
                    
                    is_api_file = any(x in file_path.lower() for x in ['controller', 'api', 'resource', 'endpoint'])
                    
                    if has_ownership_check:
                        severity = 'MEDIUM'  # Có check nhưng vẫn cần review
                    elif is_api_file:
                        severity = 'HIGH'  # API file không có check = nguy hiểm
                    elif 'findById' in desc or 'PathVariable' in desc:
                        severity = 'HIGH'
                    else:
                        severity = 'MEDIUM'
                    
                    # Skip nếu là ownership check rõ ràng trên cùng dòng
                    current_line = lines[line_num - 1] if line_num <= len(lines) else ''
                    if 'currentUser' in current_line and 'getId' in current_line:
                        continue  # findById(currentUser.getId()) là an toàn
                    
                    findings.append({
                        'file': os.path.relpath(file_path, directory_path),
                        'line': line_num,
                        'pattern': desc,
                        'code': current_line.strip()[:100],
                        'severity': severity,
                        'has_nearby_check': has_ownership_check
                    })
        except Exception as e:
            continue
    
    # Format output
    result = f"## 🔓 Scan IDOR Vulnerabilities\n\n"
    result += f"**Thư mục:** `{directory_path}`\n"
    result += f"**Files đã quét:** {len(files)}\n"
    result += f"**Potential IDOR:** {len(findings)}\n\n"
    
    if not findings:
        result += "✅ Không tìm thấy IDOR vulnerability rõ ràng!\n"
        result += "\n*Lưu ý: Vẫn cần review thủ công để đảm bảo.*\n"
        return result
    
    result += "### ⚠️ Potential IDOR Vulnerabilities:\n\n"
    
    # Sort by severity
    high_findings = [f for f in findings if f['severity'] == 'HIGH']
    medium_findings = [f for f in findings if f['severity'] == 'MEDIUM']
    
    if high_findings:
        result += "#### 🔴 HIGH Severity:\n\n"
        for item in high_findings[:15]:
            result += f"- **{item['file']}** (line {item['line']})\n"
            result += f"  - Pattern: `{item['pattern']}`\n"
            result += f"  - Code: `{item['code'][:100]}`\n\n"
    
    if medium_findings:
        result += "#### 🟠 MEDIUM Severity:\n\n"
        for item in medium_findings[:10]:
            result += f"- **{item['file']}** (line {item['line']})\n"
            result += f"  - Pattern: `{item['pattern']}`\n\n"
    
    result += "\n### 🛠️ Khuyến Nghị:\n"
    result += "1. Thêm kiểm tra ownership: `if (!resource.getUserId().equals(currentUser.getId()))`\n"
    result += "2. Sử dụng @PreAuthorize hoặc custom security annotations\n"
    result += "3. Không expose internal IDs - sử dụng UUID hoặc hashed IDs\n"
    
    return result


@tool
def scan_xss_vulnerabilities(directory_path: str) -> str:
    """
    Quét thư mục tìm XSS vulnerabilities (Cross-Site Scripting).
    Tìm dangerouslySetInnerHTML, innerHTML, document.write, v.v.
    
    Args:
        directory_path: Đường dẫn đến thư mục chứa source code
        
    Returns:
        Danh sách các potential XSS vulnerabilities
    """
    print(f"--- [Code Review] Scanning for XSS vulnerabilities in: {directory_path} ---")
    
    if not os.path.exists(directory_path):
        return f"❌ Thư mục không tồn tại: {directory_path}"
    
    # XSS patterns
    xss_patterns = [
        # React
        (r'dangerouslySetInnerHTML', 'React dangerouslySetInnerHTML', 'HIGH'),
        
        # Vanilla JS
        (r'\.innerHTML\s*=', 'innerHTML assignment', 'HIGH'),
        (r'\.outerHTML\s*=', 'outerHTML assignment', 'HIGH'),
        (r'document\.write\s*\(', 'document.write', 'HIGH'),
        (r'document\.writeln\s*\(', 'document.writeln', 'HIGH'),
        (r'eval\s*\(', 'eval() - code execution', 'CRITICAL'),
        
        # jQuery
        (r'\$\([^)]+\)\.html\s*\(', 'jQuery .html()', 'HIGH'),
        (r'\$\([^)]+\)\.append\s*\([^)]*\+', 'jQuery .append() with concatenation', 'MEDIUM'),
        
        # Template engines
        (r'\{\{\{[^}]+\}\}\}', 'Handlebars unescaped {{{', 'HIGH'),
        (r'\{!![^}]+!!\}', 'Blade unescaped {!! !!}', 'HIGH'),
        (r'<%=\s*[^%]+%>', 'EJS unescaped <%=', 'MEDIUM'),
        
        # Java/Thymeleaf
        (r'th:utext\s*=', 'Thymeleaf th:utext (unescaped)', 'HIGH'),
        
        # Vue
        (r'v-html\s*=', 'Vue v-html directive', 'HIGH'),
        
        # Angular
        (r'\[innerHTML\]\s*=', 'Angular [innerHTML]', 'HIGH'),
    ]
    
    # Safe patterns (sanitization)
    safe_patterns = [
        r'DOMPurify',
        r'sanitize',
        r'escape',
        r'encodeHTML',
        r'htmlEncode',
        r'xssFilter',
    ]
    
    extensions = ['.js', '.jsx', '.ts', '.tsx', '.vue', '.html', '.htm', '.php', '.java']
    files = get_all_files(directory_path, extensions, max_files=200)
    
    findings = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            for pattern, desc, severity in xss_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    pos = match.start()
                    line_num = content[:pos].count('\n') + 1
                    
                    # Get context
                    start_line = max(0, line_num - 3)
                    end_line = min(len(lines), line_num + 3)
                    context = '\n'.join(lines[start_line:end_line])
                    
                    # Check for sanitization
                    is_sanitized = any(
                        re.search(safe_pattern, context, re.IGNORECASE)
                        for safe_pattern in safe_patterns
                    )
                    
                    if not is_sanitized:
                        findings.append({
                            'file': os.path.relpath(file_path, directory_path),
                            'line': line_num,
                            'pattern': desc,
                            'code': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                            'severity': severity
                        })
        except Exception as e:
            continue
    
    # Format output
    result = f"## 🔓 Scan XSS Vulnerabilities\n\n"
    result += f"**Thư mục:** `{directory_path}`\n"
    result += f"**Files đã quét:** {len(files)}\n"
    result += f"**Potential XSS:** {len(findings)}\n\n"
    
    if not findings:
        result += "✅ Không tìm thấy XSS vulnerability rõ ràng!\n"
        return result
    
    result += "### ⚠️ Potential XSS Vulnerabilities:\n\n"
    
    # Group by severity
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM']:
        severity_findings = [f for f in findings if f['severity'] == severity]
        if severity_findings:
            emoji = '🔴' if severity == 'CRITICAL' else '🟠' if severity == 'HIGH' else '🟡'
            result += f"#### {emoji} {severity} ({len(severity_findings)} findings)\n\n"
            
            for item in severity_findings[:10]:
                result += f"- **{item['file']}** (line {item['line']})\n"
                result += f"  - Pattern: `{item['pattern']}`\n"
                result += f"  - Code: `{item['code'][:80]}`\n\n"
            
            if len(severity_findings) > 10:
                result += f"- ... và {len(severity_findings) - 10} findings khác\n\n"
    
    result += "\n### 🛠️ Khuyến Nghị:\n"
    result += "1. Sử dụng DOMPurify để sanitize HTML trước khi render\n"
    result += "2. Tránh dùng dangerouslySetInnerHTML - render components thay thế\n"
    result += "3. Escape output trên server-side trước khi trả về\n"
    result += "4. Implement Content-Security-Policy header\n"
    
    return result


@tool
def analyze_security_config(directory_path: str) -> str:
    """
    Phân tích cấu hình bảo mật trong project.
    Tìm: CSRF disabled, CORS misconfiguration, excessive whitelists, v.v.
    
    Args:
        directory_path: Đường dẫn đến thư mục chứa source code
        
    Returns:
        Phân tích cấu hình bảo mật với recommendations
    """
    print(f"--- [Code Review] Analyzing security config in: {directory_path} ---")
    
    if not os.path.exists(directory_path):
        return f"❌ Thư mục không tồn tại: {directory_path}"
    
    findings = []
    
    # Security misconfigurations to look for
    security_patterns = {
        'csrf_disabled': {
            'patterns': [
                r'csrf\s*\(\s*\)\s*\.\s*disable',
                r'\.csrf\s*\(\s*AbstractHttpConfigurer::disable\s*\)',
                r'csrf:\s*false',
                r'csrfProtection:\s*false',
            ],
            'severity': 'HIGH',
            'description': 'CSRF Protection Disabled',
            'recommendation': 'Enable CSRF protection cho stateful applications'
        },
        'cors_misconfigured': {
            'patterns': [
                r'allowedOrigins\s*\(\s*["\']?\*["\']?\s*\)',
                r'Access-Control-Allow-Origin.*\*',
                r'cors\s*\(\s*\)\s*\.\s*disable',
                r'\.addMapping\s*\(\s*["\']\/\*\*["\']',
            ],
            'severity': 'MEDIUM',
            'description': 'CORS allows all origins',
            'recommendation': 'Specify allowed origins explicitly'
        },
        'auth_whitelist': {
            'patterns': [
                r'AUTH_WHITELIST\s*=\s*\{[^}]+\}',
                r'permitAll\s*\(\s*\)',
                r'antMatchers\s*\([^)]+\)\s*\.\s*permitAll',
                r'requestMatchers\s*\([^)]+\)\s*\.\s*permitAll',
            ],
            'severity': 'INFO',
            'description': 'Authentication whitelist found',
            'recommendation': 'Review whitelist - ensure only public endpoints are included'
        },
        'debug_enabled': {
            'patterns': [
                r'debug\s*[=:]\s*true',
                r'DEBUG\s*=\s*True',
                r'logging\.level\s*[=:]\s*DEBUG',
            ],
            'severity': 'LOW',
            'description': 'Debug mode enabled',
            'recommendation': 'Disable debug mode in production'
        },
        'insecure_randomness': {
            'patterns': [
                r'Math\.random\s*\(\s*\)',
                r'random\.random\s*\(\s*\)',
                r'new Random\s*\(\s*\)',
            ],
            'severity': 'MEDIUM',
            'description': 'Insecure randomness for security-sensitive operations',
            'recommendation': 'Use SecureRandom or crypto.getRandomValues()'
        },
        'weak_crypto': {
            'patterns': [
                r'MD5',
                r'SHA1[^0-9]',
                r'DES[^3]',
                r'RC4',
            ],
            'severity': 'HIGH',
            'description': 'Weak cryptographic algorithm',
            'recommendation': 'Use SHA-256 or stronger, AES-256'
        },
    }
    
    # Get all config and security-related files
    extensions = ['.java', '.py', '.js', '.ts', '.yml', '.yaml', '.json', '.xml', '.properties']
    files = get_all_files(directory_path, extensions, max_files=300)
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            for config_type, config_info in security_patterns.items():
                for pattern in config_info['patterns']:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        pos = match.start()
                        line_num = content[:pos].count('\n') + 1
                        
                        findings.append({
                            'type': config_type,
                            'file': os.path.relpath(file_path, directory_path),
                            'line': line_num,
                            'code': lines[line_num - 1].strip() if line_num <= len(lines) else '',
                            'severity': config_info['severity'],
                            'description': config_info['description'],
                            'recommendation': config_info['recommendation']
                        })
        except Exception as e:
            continue
    
    # Format output
    result = f"## 🔧 Security Configuration Analysis\n\n"
    result += f"**Thư mục:** `{directory_path}`\n"
    result += f"**Files đã quét:** {len(files)}\n"
    result += f"**Issues tìm thấy:** {len(findings)}\n\n"
    
    if not findings:
        result += "✅ Không tìm thấy security misconfiguration rõ ràng!\n"
        return result
    
    result += "### ⚠️ Security Configuration Issues:\n\n"
    
    # Group by severity
    severity_order = ['HIGH', 'MEDIUM', 'LOW', 'INFO']
    severity_emoji = {'HIGH': '🔴', 'MEDIUM': '🟠', 'LOW': '🟡', 'INFO': '🔵'}
    
    for severity in severity_order:
        severity_findings = [f for f in findings if f['severity'] == severity]
        if severity_findings:
            result += f"#### {severity_emoji[severity]} {severity}\n\n"
            
            # Group by type within severity
            seen_types = set()
            for item in severity_findings:
                if item['type'] not in seen_types:
                    seen_types.add(item['type'])
                    result += f"**{item['description']}**\n"
                    result += f"- 📁 Files: "
                    
                    type_files = [f for f in severity_findings if f['type'] == item['type']]
                    for f in type_files[:5]:
                        result += f"`{f['file']}:{f['line']}` "
                    if len(type_files) > 5:
                        result += f"(+{len(type_files) - 5} more)"
                    result += "\n"
                    result += f"- 💡 Recommendation: {item['recommendation']}\n\n"
    
    return result


# === COMBINED FULL SCAN ===

@tool
def full_security_scan(directory_path: str) -> str:
    """
    Thực hiện full security scan trên một thư mục.
    Bao gồm: Hardcoded credentials, IDOR, XSS, và Security config.
    
    Args:
        directory_path: Đường dẫn đến thư mục cần scan
        
    Returns:
        Báo cáo bảo mật đầy đủ
    """
    print(f"--- [Code Review] Starting FULL security scan: {directory_path} ---")
    
    if not os.path.exists(directory_path):
        return f"❌ Thư mục không tồn tại: {directory_path}"
    
    result = f"# 🔒 Full Security Scan Report\n\n"
    result += f"**Target:** `{directory_path}`\n"
    result += f"**Scan Time:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    result += "---\n\n"
    
    # Run all scans
    result += "## 1. Hardcoded Credentials\n\n"
    cred_result = scan_hardcoded_credentials.invoke({"directory_path": directory_path})
    result += cred_result.replace("## 🔐 Scan Hardcoded Credentials", "").strip() + "\n\n"
    result += "---\n\n"
    
    result += "## 2. IDOR Vulnerabilities\n\n"
    idor_result = scan_idor_vulnerabilities.invoke({"directory_path": directory_path})
    result += idor_result.replace("## 🔓 Scan IDOR Vulnerabilities", "").strip() + "\n\n"
    result += "---\n\n"
    
    result += "## 3. XSS Vulnerabilities\n\n"
    xss_result = scan_xss_vulnerabilities.invoke({"directory_path": directory_path})
    result += xss_result.replace("## 🔓 Scan XSS Vulnerabilities", "").strip() + "\n\n"
    result += "---\n\n"
    
    result += "## 4. Security Configuration\n\n"
    config_result = analyze_security_config.invoke({"directory_path": directory_path})
    result += config_result.replace("## 🔧 Security Configuration Analysis", "").strip() + "\n\n"
    
    result += "---\n\n"
    result += "## 📋 Summary\n\n"
    result += "Scan hoàn tất. Vui lòng review các findings và thực hiện remediation theo recommendations.\n"
    
    return result


# === IMPORT SOURCE CODE TO RAG ===

@tool
def import_source_to_rag(
    directory_path: str,
    file_types: str = "all",
    max_files: int = 50,
    project_name: str = ""
) -> str:
    """
    Import source code từ thư mục vào RAG (FAISS index).
    Cho phép AI tìm kiếm và trả lời câu hỏi về code.
    
    Args:
        directory_path: Đường dẫn tuyệt đối đến thư mục chứa source code
        file_types: "all", "java", "javascript", "python", "config", "web"
        max_files: Số file tối đa để import (mặc định 50, tối đa 100)
        project_name: Tên project (dùng làm source name trong RAG)
        
    Returns:
        Kết quả import với số files và chunks đã thêm vào RAG
    """
    print(f"--- [Code Review] Importing source code to RAG: {directory_path} ---")
    
    if not os.path.exists(directory_path):
        return f"❌ Thư mục không tồn tại: {directory_path}"
    
    if not os.path.isdir(directory_path):
        return f"❌ Đường dẫn không phải là thư mục: {directory_path}"
    
    # Limit max_files
    max_files = min(max_files, 100)
    
    # Determine project name
    if not project_name:
        project_name = os.path.basename(directory_path)
    
    # Get extensions
    if file_types == "all":
        extensions = ALL_EXTENSIONS
    elif file_types in SUPPORTED_EXTENSIONS:
        extensions = SUPPORTED_EXTENSIONS[file_types]
    else:
        extensions = ALL_EXTENSIONS
    
    # Get files
    files = get_all_files(directory_path, extensions, max_files=max_files)
    
    if not files:
        return f"❌ Không tìm thấy file {file_types} nào trong {directory_path}"
    
    print(f"--- [Code Review] Found {len(files)} files to import ---")
    
    # Import dependencies
    try:
        import sys
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        
        from langchain_core.documents import Document
        from utils.document_processor import chunk_documents, add_to_faiss
        from utils.source_manager import add_source, update_source_chunks
    except ImportError as e:
        return f"❌ Lỗi import dependencies: {e}"
    
    # Process files into documents
    documents = []
    processed_files = []
    errors = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                continue
            
            # Get relative path for metadata
            rel_path = os.path.relpath(file_path, directory_path)
            
            # Get file extension for language detection
            ext = os.path.splitext(file_path)[1].lower()
            lang_map = {
                '.java': 'java', '.py': 'python', '.js': 'javascript',
                '.ts': 'typescript', '.tsx': 'tsx', '.jsx': 'jsx',
                '.yml': 'yaml', '.yaml': 'yaml', '.json': 'json',
                '.xml': 'xml', '.html': 'html', '.php': 'php'
            }
            language = lang_map.get(ext, 'code')
            
            # Create document with rich metadata
            doc_content = f"""## File: {rel_path}
**Project:** {project_name}
**Language:** {language}
**Path:** {file_path}

```{language}
{content}
```
"""
            
            doc = Document(
                page_content=doc_content,
                metadata={
                    'source': f"{project_name}/{rel_path}",
                    'file_path': file_path,
                    'project': project_name,
                    'language': language,
                    'type': 'source_code'
                }
            )
            
            documents.append(doc)
            processed_files.append(rel_path)
            
        except Exception as e:
            errors.append(f"{file_path}: {str(e)[:50]}")
            continue
    
    if not documents:
        return f"❌ Không thể đọc file nào từ {directory_path}"
    
    print(f"--- [Code Review] Created {len(documents)} documents ---")
    
    # Chunk documents (smaller chunks for code - 800 chars with 100 overlap)
    try:
        chunks = chunk_documents(documents, chunk_size=800, chunk_overlap=100)
        print(f"--- [Code Review] Created {len(chunks)} chunks ---")
    except Exception as e:
        return f"❌ Lỗi chunking documents: {e}"
    
    # Add to FAISS
    try:
        success, message = add_to_faiss(chunks)
        
        if not success:
            return f"❌ Lỗi thêm vào FAISS: {message}"
        
        print(f"--- [Code Review] {message} ---")
    except Exception as e:
        return f"❌ Lỗi FAISS: {e}"
    
    # Try to add source metadata (optional)
    try:
        total_size = sum(os.path.getsize(f) for f in files if os.path.exists(f))
        add_source(
            name=f"[CODE] {project_name}",
            type="source_code",
            size=total_size,
            path=directory_path,  # Save absolute path
            summary=f"Source code từ {project_name} ({len(files)} files, {len(chunks)} chunks)",
            suggested_questions=[
                f"Tìm hardcoded credentials trong {project_name}",
                f"Phân tích cấu trúc dự án {project_name}",
                f"Tìm lỗ hổng bảo mật trong {project_name}",
            ]
        )
        update_source_chunks(f"[CODE] {project_name}", len(chunks))
    except Exception as e:
        print(f"--- [Code Review] Warning: Could not add source metadata: {e} ---")
    
    # Format result
    result = f"## ✅ Import Source Code Thành Công!\n\n"
    result += f"**Project:** `{project_name}`\n"
    result += f"**Thư mục:** `{directory_path}`\n"
    result += f"**Loại file:** {file_types}\n\n"
    result += f"### 📊 Thống Kê:\n\n"
    result += f"- **Files đã import:** {len(processed_files)}\n"
    result += f"- **Chunks tạo ra:** {len(chunks)}\n"
    result += f"- **Errors:** {len(errors)}\n\n"
    
    if processed_files:
        result += "### 📁 Files Đã Import:\n\n"
        for f in processed_files[:20]:
            result += f"- `{f}`\n"
        if len(processed_files) > 20:
            result += f"- ... và {len(processed_files) - 20} files khác\n"
        result += "\n"
    
    if errors:
        result += "### ⚠️ Errors:\n\n"
        for e in errors[:5]:
            result += f"- {e}\n"
        result += "\n"
    
    result += "### 💡 Bây Giờ Bạn Có Thể Hỏi:\n\n"
    result += f"1. \"Tìm hardcoded credentials trong {project_name}\"\n"
    result += f"2. \"Phân tích file Const.java trong {project_name}\"\n"
    result += f"3. \"Tìm lỗ hổng IDOR trong {project_name}\"\n"
    result += f"4. \"Giải thích SecurityConfiguration trong {project_name}\"\n"
    
    return result


# === LIST IMPORTED PROJECTS ===

@tool
def list_imported_projects() -> str:
    """
    Liệt kê các projects source code đã được import vào RAG cùng với đường dẫn.
    Giúp AI nhớ lại đường dẫn project để thực hiện các task khác (như scan, search).
    
    Returns:
        Danh sách projects và đường dẫn
    """
    try:
        import sys
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
            
        from utils.source_manager import load_sources
        
        sources = load_sources()
        code_projects = [s for s in sources if s.get('type') == 'source_code' or s.get('name', '').startswith('[CODE]')]
        
        if not code_projects:
            return "❌ Chưa có project source code nào được import vào RAG."
            
        result = "## 📚 Danh Sách Projects Đã Import:\n\n"
        for p in code_projects:
            path = p.get('path', 'N/A')
            name = p.get('name', 'Unknown')
            chunks = p.get('chunks', 0)
            uploaded_at = p.get('uploaded_at', '').split('T')[0]
            
            result += f"- **{name}**\n"
            result += f"  - Path: `{path}`\n"
            result += f"  - Chunks: {chunks}\n"
            result += f"  - Ngày import: {uploaded_at}\n\n"
            
        return result
        
    except Exception as e:
        return f"❌ Lỗi lấy danh sách projects: {e}"


# === DELETE SOURCE FROM RAG ===

@tool
def delete_source_from_rag(source_name: str) -> str:
    """
    Xóa một source đã import khỏi RAG.
    
    Args:
        source_name: Tên source cần xóa (ví dụ: "[CODE] Bookstore")
        
    Returns:
        Kết quả xóa
    """
    print(f"--- [Code Review] Deleting source from RAG: {source_name} ---")
    
    try:
        import sys
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        
        from utils.source_manager import delete_source, load_sources
        
        # Kiểm tra source có tồn tại không
        sources = load_sources()
        source_names = [s['name'] for s in sources]
        
        if source_name not in source_names:
            return f"❌ Không tìm thấy source: `{source_name}`\n\n**Các sources hiện có:**\n" + "\n".join([f"- {s}" for s in source_names])
        
        # Xóa source
        success = delete_source(source_name)
        
        if success:
            return f"✅ Đã xóa source `{source_name}` khỏi RAG!\n\nBạn có thể import lại nếu cần."
        else:
            return f"❌ Không thể xóa source: {source_name}"
            
    except Exception as e:
        return f"❌ Lỗi xóa source: {e}"


# === SEARCH PATTERN IN CODE ===

@tool
def search_pattern_in_code(
    directory_path: str,
    pattern: str,
    file_types: str = "all",
    context_lines: int = 3
) -> str:
    """
    Tìm kiếm một pattern cụ thể trong source code và trả về kết quả với context.
    
    Args:
        directory_path: Đường dẫn thư mục chứa code
        pattern: Pattern cần tìm (regex hoặc text thường)
        file_types: "all", "java", "javascript", "python", "config"
        context_lines: Số dòng context trước và sau (mặc định 3)
        
    Returns:
        Danh sách các matches với file, line, và context
    """
    print(f"--- [Code Review] Searching for pattern '{pattern}' in {directory_path} ---")
    
    if not os.path.exists(directory_path):
        return f"❌ Thư mục không tồn tại: {directory_path}"
    
    # Get extensions
    if file_types == "all":
        extensions = ALL_EXTENSIONS
    elif file_types in SUPPORTED_EXTENSIONS:
        extensions = SUPPORTED_EXTENSIONS[file_types]
    else:
        extensions = ALL_EXTENSIONS
    
    files = get_all_files(directory_path, extensions, max_files=200)
    
    findings = []
    
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Tìm tất cả matches
            for match in re.finditer(pattern, content, re.IGNORECASE):
                pos = match.start()
                line_num = content[:pos].count('\n') + 1
                
                # Lấy context
                start = max(0, line_num - context_lines - 1)
                end = min(len(lines), line_num + context_lines)
                context = lines[start:end]
                
                findings.append({
                    'file': os.path.relpath(file_path, directory_path),
                    'line': line_num,
                    'match': match.group(0)[:100],
                    'context': context,
                    'context_start': start + 1
                })
                
        except Exception as e:
            continue
    
    # Format output
    result = f"## 🔍 Search Results: `{pattern}`\n\n"
    result += f"**Thư mục:** `{directory_path}`\n"
    result += f"**Files đã quét:** {len(files)}\n"
    result += f"**Matches:** {len(findings)}\n\n"
    
    if not findings:
        result += f"❌ Không tìm thấy pattern `{pattern}` trong {len(files)} files.\n"
        return result
    
    result += "### 📋 Kết Quả:\n\n"
    
    for i, item in enumerate(findings[:20], 1):
        result += f"#### {i}. `{item['file']}` (line {item['line']})\n\n"
        result += "```java\n"
        for j, line in enumerate(item['context'], start=item['context_start']):
            marker = ">>> " if j == item['line'] else "    "
            result += f"{j:4d}: {marker}{line}\n"
        result += "```\n\n"
    
    if len(findings) > 20:
        result += f"... và {len(findings) - 20} kết quả khác\n\n"
    
    return result

