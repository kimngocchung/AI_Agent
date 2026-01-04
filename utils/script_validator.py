# File: utils/script_validator.py
"""
Script Validator Module
Kiểm tra cú pháp và security patterns của scripts trước khi thực thi.
"""

import ast
import re
import subprocess
import tempfile
import os
from typing import Tuple, List, Dict
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Kết quả validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    security_issues: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "security_issues": self.security_issues
        }


# ==============================================================================
# DANGEROUS PATTERNS - Các pattern nguy hiểm cần cảnh báo
# ==============================================================================

DANGEROUS_PYTHON_PATTERNS = [
    # File system destruction
    (r"shutil\.rmtree\s*\(['\"]\/", "Xóa thư mục hệ thống gốc"),
    (r"os\.remove\s*\(['\"]\/etc", "Xóa file cấu hình hệ thống"),
    (r"os\.unlink\s*\(['\"]\/", "Xóa file hệ thống"),
    
    # System manipulation
    (r"os\.system\s*\(['\"]rm\s+-rf\s+\/", "Lệnh rm -rf nguy hiểm"),
    (r"subprocess\..*\(['\"]rm\s+-rf", "Subprocess rm -rf nguy hiểm"),
    
    # Privilege escalation hints
    (r"chmod\s+777\s+\/", "Thay đổi quyền file hệ thống"),
    (r"\/etc\/passwd", "Truy cập file passwd (cần review)"),
    (r"\/etc\/shadow", "Truy cập file shadow (cần review)"),
    
    # Network dangers
    (r"reverse.*shell", "Có thể là reverse shell (cần review)"),
    (r"bind.*shell", "Có thể là bind shell (cần review)"),
    
    # Code execution from external
    (r"eval\s*\(\s*input\s*\(", "Eval input trực tiếp - nguy hiểm"),
    (r"exec\s*\(\s*input\s*\(", "Exec input trực tiếp - nguy hiểm"),
    (r"__import__\s*\(\s*input", "Import động từ input - nguy hiểm"),
]

DANGEROUS_BASH_PATTERNS = [
    # Destructive commands
    (r"rm\s+-rf\s+\/(?!\s)", "Lệnh rm -rf trên thư mục gốc"),
    (r"rm\s+-rf\s+\/\*", "Xóa toàn bộ hệ thống"),
    (r"dd\s+if=.*of=\/dev\/sd", "Ghi trực tiếp vào disk"),
    (r"mkfs\.", "Format filesystem"),
    (r":\(\)\{\s*:\|:\s*&\s*\};:", "Fork bomb detected"),
    
    # Privilege issues
    (r"chmod\s+-R\s+777\s+\/", "Chmod 777 recursive trên root"),
    (r"chown\s+-R\s+.*\s+\/(?!\s)", "Chown recursive trên root"),
    
    # Dangerous downloads
    (r"curl.*\|\s*bash", "Pipe curl vào bash - nguy hiểm"),
    (r"wget.*\|\s*sh", "Pipe wget vào shell - nguy hiểm"),
    
    # Credentials
    (r"\/etc\/shadow", "Truy cập shadow file (cần review)"),
    (r"\.ssh\/id_rsa", "Truy cập SSH private key (cần review)"),
]

# Patterns yêu cầu warning nhưng không block
WARNING_PATTERNS = [
    (r"requests\.get\s*\([^)]*verify\s*=\s*False", "SSL verification disabled"),
    (r"urllib3\.disable_warnings", "SSL warnings disabled"),
    (r"timeout\s*=\s*None", "Không có timeout - có thể bị treo"),
    (r"password\s*=\s*['\"][^'\"]+['\"]", "Hardcoded password detected"),
    (r"api_key\s*=\s*['\"][^'\"]+['\"]", "Hardcoded API key detected"),
]


# ==============================================================================
# PYTHON VALIDATION
# ==============================================================================

def validate_python_syntax(script: str) -> Tuple[bool, List[str]]:
    """
    Kiểm tra cú pháp Python bằng ast.parse()
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    try:
        ast.parse(script)
        return True, []
    except SyntaxError as e:
        errors.append(f"Lỗi cú pháp dòng {e.lineno}: {e.msg}")
        if e.text:
            errors.append(f"  → {e.text.strip()}")
        return False, errors
    except Exception as e:
        errors.append(f"Lỗi parse: {str(e)}")
        return False, errors


def is_script_truncated(script: str) -> Tuple[bool, str]:
    """
    Kiểm tra xem script có bị cắt ngắn (truncated) không.
    
    Các dấu hiệu script bị truncated:
    - Kết thúc bằng dấu chấm (như `parser.`, `args.`)
    - Kết thúc bằng dấu phẩy, dấu hai chấm, dấu mở ngoặc
    - Thiếu if __name__ == "__main__" hoặc kết thúc hàm main()
    - Số dấu mở/đóng ngoặc không khớp
    
    Returns:
        (is_truncated: bool, last_line: str)
    """
    if not script or not script.strip():
        return True, ""
    
    lines = script.strip().split('\n')
    last_line = lines[-1].strip() if lines else ""
    
    # Patterns indicating truncation
    truncation_patterns = [
        # Ends with incomplete statement
        r'^[a-zA-Z_][a-zA-Z0-9_]*\.$',  # e.g., "parser.", "args."
        r'^[a-zA-Z_][a-zA-Z0-9_]*\.\s*$',
        r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\($',  # ends with open paren
        r'^.*,$',  # ends with comma (incomplete list/dict)
        r'^.*:$',  # ends with colon (incomplete block) - except valid def/if/etc
        r'^.*\($',  # ends with open paren
        r'^.*\[$',  # ends with open bracket
        r'^.*\{$',  # ends with open brace
    ]
    
    # Check last line patterns
    for pattern in truncation_patterns:
        if re.match(pattern, last_line):
            # Exception: valid block starters
            if last_line.endswith(':'):
                block_starters = ['if ', 'elif ', 'else:', 'for ', 'while ', 'def ', 'class ', 'try:', 'except', 'finally:', 'with ']
                if any(last_line.strip().startswith(s) or last_line.strip() == s.strip() for s in block_starters):
                    continue
            return True, last_line
    
    # Check for unbalanced brackets
    open_parens = script.count('(') - script.count(')')
    open_brackets = script.count('[') - script.count(']')
    open_braces = script.count('{') - script.count('}')
    
    if open_parens > 0 or open_brackets > 0 or open_braces > 0:
        return True, f"Unbalanced: ( +{open_parens}, [ +{open_brackets}, {{ +{open_braces}"
    
    # Check for missing main
    has_main = "if __name__" in script or 'def main()' in script
    has_argparse = "argparse" in script or "ArgumentParser" in script
    
    # If script uses argparse but doesn't have a complete main, likely truncated
    if has_argparse and not has_main:
        return True, "Has argparse but missing main()"
    
    # Check if script has many lines but ends abruptly
    if len(lines) > 50 and not (
        last_line.startswith('if __name__') or 
        last_line == 'main()' or 
        last_line.startswith('#') or
        last_line == '' or
        last_line.startswith('sys.exit')
    ):
        # Check if it looks incomplete
        if re.match(r'^[a-zA-Z_]', last_line) and not last_line.endswith(')'):
            if not last_line.endswith('"') and not last_line.endswith("'"):
                return True, last_line
    
    return False, ""


def check_python_imports(script: str) -> List[str]:
    """
    Kiểm tra các import trong script Python
    
    Returns:
        List các warning về imports
    """
    warnings = []
    
    # Các module nguy hiểm cần cảnh báo
    dangerous_imports = [
        ("ctypes", "Module thao tác bộ nhớ cấp thấp"),
        ("pty", "Module tạo pseudo-terminal"),
        ("fcntl", "Module điều khiển file descriptor"),
    ]
    
    try:
        tree = ast.parse(script)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for mod, desc in dangerous_imports:
                        if alias.name == mod or alias.name.startswith(f"{mod}."):
                            warnings.append(f"Import '{alias.name}': {desc}")
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for mod, desc in dangerous_imports:
                        if node.module == mod or node.module.startswith(f"{mod}."):
                            warnings.append(f"Import từ '{node.module}': {desc}")
    
    except:
        pass  # Ignore parse errors here, syntax validation handles it
    
    return warnings


# ==============================================================================
# BASH VALIDATION
# ==============================================================================

def validate_bash_syntax(script: str) -> Tuple[bool, List[str]]:
    """
    Kiểm tra cú pháp Bash bằng bash -n
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    try:
        # Tạo file tạm
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script)
            temp_path = f.name
        
        # Chạy bash -n để check syntax
        result = subprocess.run(
            ['bash', '-n', temp_path],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Xóa file tạm
        os.unlink(temp_path)
        
        if result.returncode != 0:
            # Parse error output
            for line in result.stderr.split('\n'):
                if line.strip():
                    errors.append(line.strip())
            return False, errors
        
        return True, []
        
    except FileNotFoundError:
        # bash không có sẵn (Windows)
        return True, ["⚠️ Không thể kiểm tra Bash syntax (bash không khả dụng)"]
    except subprocess.TimeoutExpired:
        return False, ["Timeout khi kiểm tra syntax"]
    except Exception as e:
        return True, [f"⚠️ Không thể kiểm tra Bash syntax: {e}"]


# ==============================================================================
# SECURITY PATTERN CHECKING
# ==============================================================================

def check_dangerous_patterns(script: str, script_type: str) -> List[str]:
    """
    Kiểm tra các pattern nguy hiểm trong script
    
    Returns:
        List các security issues
    """
    issues = []
    
    patterns = DANGEROUS_PYTHON_PATTERNS if script_type == "python" else DANGEROUS_BASH_PATTERNS
    
    for pattern, description in patterns:
        if re.search(pattern, script, re.IGNORECASE):
            issues.append(f"⚠️ SECURITY: {description}")
    
    return issues


def check_warning_patterns(script: str) -> List[str]:
    """
    Kiểm tra các pattern cần cảnh báo (không block)
    
    Returns:
        List các warnings
    """
    warnings = []
    
    for pattern, description in WARNING_PATTERNS:
        if re.search(pattern, script, re.IGNORECASE):
            warnings.append(f"⚠️ {description}")
    
    return warnings


# ==============================================================================
# MAIN VALIDATION FUNCTION
# ==============================================================================

def validate_script(script: str, script_type: str = "python") -> ValidationResult:
    """
    Hàm validation chính - kiểm tra script toàn diện.
    
    Args:
        script: Nội dung script
        script_type: "python" hoặc "bash"
        
    Returns:
        ValidationResult với is_valid, errors, warnings, security_issues
    """
    errors = []
    warnings = []
    security_issues = []
    
    # 1. Kiểm tra syntax
    if script_type == "python":
        is_valid, syntax_errors = validate_python_syntax(script)
        errors.extend(syntax_errors)
        
        # Check imports
        import_warnings = check_python_imports(script)
        warnings.extend(import_warnings)
        
    elif script_type == "bash":
        is_valid, syntax_errors = validate_bash_syntax(script)
        errors.extend(syntax_errors)
    else:
        is_valid = True
        warnings.append(f"Không hỗ trợ validate script type: {script_type}")
    
    # 2. Kiểm tra dangerous patterns
    security_issues = check_dangerous_patterns(script, script_type)
    
    # 3. Kiểm tra warning patterns
    warnings.extend(check_warning_patterns(script))
    
    # 4. Quyết định is_valid
    # Chỉ block nếu có syntax errors hoặc security issues nghiêm trọng
    # Security issues chỉ là warnings, không block
    final_valid = is_valid and len(errors) == 0
    
    return ValidationResult(
        is_valid=final_valid,
        errors=errors,
        warnings=warnings,
        security_issues=security_issues
    )


def format_validation_result(result: ValidationResult) -> str:
    """
    Format ValidationResult thành string đẹp để hiển thị
    """
    lines = []
    
    if result.is_valid:
        lines.append("✅ **Script hợp lệ**")
    else:
        lines.append("❌ **Script không hợp lệ**")
    
    if result.errors:
        lines.append("\n**Lỗi:**")
        for error in result.errors:
            lines.append(f"  - {error}")
    
    if result.security_issues:
        lines.append("\n**Cảnh báo bảo mật:**")
        for issue in result.security_issues:
            lines.append(f"  - {issue}")
    
    if result.warnings:
        lines.append("\n**Lưu ý:**")
        for warning in result.warnings:
            lines.append(f"  - {warning}")
    
    return "\n".join(lines)


# ==============================================================================
# TEST
# ==============================================================================

if __name__ == "__main__":
    # Test Python script
    test_python = '''
import requests
import os

def scan(url):
    response = requests.get(url, verify=False, timeout=10)
    return response.status_code

if __name__ == "__main__":
    print(scan("http://example.com"))
'''
    
    print("Testing Python script:")
    result = validate_script(test_python, "python")
    print(format_validation_result(result))
    
    print("\n" + "="*50 + "\n")
    
    # Test dangerous Python
    dangerous_python = '''
import os
os.system("rm -rf /")
'''
    
    print("Testing dangerous Python:")
    result = validate_script(dangerous_python, "python")
    print(format_validation_result(result))
    
    print("\n" + "="*50 + "\n")
    
    # Test invalid Python
    invalid_python = '''
def broken(
    print("missing closing paren"
'''
    
    print("Testing invalid Python:")
    result = validate_script(invalid_python, "python")
    print(format_validation_result(result))
