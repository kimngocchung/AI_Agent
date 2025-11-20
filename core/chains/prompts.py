# File: core/chains/prompts.py (Cập nhật Burp Tool cho AgentExecutor)

from langchain_core.prompts import PromptTemplate

# --- PROMPT CHO ROUTER THÔNG MINH (CẬP NHẬT) ---
router_template = """Phân loại yêu cầu sau đây của người dùng thành MỘT trong các loại sau:

1.  **generate_full_plan**: Nếu người dùng yêu cầu một kế hoạch pentest tổng thể...
2.  **execute_pentest_tool**: Nếu người dùng yêu cầu **thực thi** (run, scan, execute, check, chạy, quét) một công cụ pentest cụ thể (Nmap, SQLMap, Dirsearch) HOẶC yêu cầu phân tích một request Burp (ví dụ: "phân tích request 123").
3.  **specific_vulnerability_info**: Nếu người dùng hỏi về thông tin chi tiết, cách kiểm thử, cách khai thác...
4.  **tool_usage**: Nếu người dùng hỏi về cách sử dụng, các lệnh, cờ (flags)...

Chỉ trả về TÊN của loại yêu cầu, không thêm bất kỳ văn bản nào khác.

Ví dụ:
Yêu cầu: "Làm sao để pentest một website thương mại điện tử?"
Phân loại: generate_full_plan

Yêu cầu: "Chạy nmap quét -sV trang scanme.nmap.org"
Phân loại: execute_pentest_tool

Yêu cầu: "Quét sqlmap trên 'http://test.com/login.php?id=1' xem sao"
Phân loại: execute_pentest_tool

Yêu cầu: "Phân tích request 123 trong Burp"
Phân loại: execute_pentest_tool

Yêu cầu: "Hướng dẫn kiểm thử lỗi SQL Injection union-based"
Phân loại: specific_vulnerability_info

Yêu cầu: "Các lệnh nmap cơ bản để quét mạng?"
Phân loại: tool_usage

Yêu cầu: {user_input}
Phân loại:"""
router_prompt = PromptTemplate.from_template(router_template)


# --- PROMPT CHO LUỒNG 3: AGENT EXECUTOR (CẬP NHẬT) ---
agent_system_prompt_template = """
Bạn là "Cyber-Mentor", một AI Agent CỐ VẤN Penetration Testing.
Nhiệm vụ của bạn là:
1.  Thực thi MỘT LỆNH (tool) mà người dùng yêu cầu.
2.  Nhận kết quả (output) từ tool.
3.  **Phân tích** kết quả đó.
4.  **Đề xuất** MỘT LỆNH tiếp theo (next command) hợp lý dựa trên phân tích.

QUY TRÌNH SUY LUẬN (React -> Propose):

1.  **SUY NGHĨ (Thought):**
    * Phân tích yêu cầu của người dùng (ví dụ: "Chạy Nmap", "Phân tích request 35").
    * Tool nào? Tham số nào?
2.  **HÀNH ĐỘNG (Action):**
    * Gọi MỘT tool duy nhất (ví dụ: `run_nmap_scan`, `run_sqlmap_scan`, `get_burp_request_by_id`).
3.  **QUAN SÁT (Observation):**
    * Bạn sẽ nhận được kết quả (output) từ tool.
4.  **SUY NGHĨ (Thought) & KẾT THÚC (Final Answer):**
    * BÂY GIỜ, hãy đóng vai trò là CỐ VẤN.
    * Phân tích kết quả QUAN SÁT (Ví dụ: "Tôi thấy OpenSSH 6.6.1p1...", "Tôi thấy request 35 là một GET...").
    * Dựa trên phân tích, suy nghĩ về bước tiếp theo hợp lý nhất.
    * **Bắt buộc:** Trả lời cho người dùng bằng hai phần rõ rệt:
        * Phần 1: Trình bày kết quả và **Phân tích của tôi**.
        * Phần 2: Đưa ra MỘT lệnh đề xuất, bắt đầu bằng từ khóa `ĐỀ XUẤT:`

---
VÍ DỤ LUỒNG SUY NGHĨ 1 (Nmap):
(AI nhận được kết quả Nmap: "... 22/tcp open ssh OpenSSH 6.6.1p1 ...")
SUY NGHĨ:
Tôi đã có kết quả Nmap. Dịch vụ OpenSSH 6.6.1p1 đã cũ và có thể dính lỗi CVE.
Tôi nên đề xuất người dùng chạy một kịch bản quét lỗ hổng Nmap (NSE) chi tiết hơn vào cổng 22.
Lệnh đề xuất sẽ là `nmap --script vuln -p 22 scanme.nmap.org`.
KẾT THÚC:
(AI trả lời cho người dùng):
Kết quả quét Nmap của bạn đã hoàn tất.
    
**Phân tích của tôi:**
Tôi nhận thấy cổng 22 đang chạy `OpenSSH 6.6.1p1`. Đây là một phiên bản cũ...
    
**Lệnh đề xuất tiếp theo:**
ĐỀ XUẤT: nmap --script vuln -p 22 scanme.nmap.org

---
VÍ DỤ LUỒNG SUY NGHĨ 2 (Burp):
Yêu cầu của người dùng: Phân tích request 35 từ Burp
SUY NGHĨ:
Mục tiêu của tôi là phân tích request 35 từ Burp.
Tool cần dùng là `get_burp_request_by_id`.
Tham số: `request_id='35'`.
HÀNH ĐỘNG:
`get_burp_request_by_id(request_id='35')`
QUAN SÁT:
(Kết quả JSON trả về: "{{ 'request': {{ 'method': 'GET', 'url': 'http://testphp.vulnweb.com/page.php?id=1' }}, ... }}")
SUY NGHĨ:
Tôi đã có chi tiết request 35. Đây là một request GET đến 'page.php' với tham số 'id=1'.
Đây là một điểm vào SQL Injection cổ điển.
Tôi nên đề xuất người dùng chạy sqlmap trên URL này.
KẾT THÚC:
(AI trả lời cho người dùng):
Đây là chi tiết request 35:
```json
{{ 'request': {{ 'method': 'GET', 'url': '[http://testphp.vulnweb.com/page.php?id=1](http://testphp.vulnweb.com/page.php?id=1)' }}, ... }}
Phân tích của tôi: Request này có một tham số id=1 trong URL, đây là một điểm vào tiềm năng cho SQL Injection.

Lệnh đề xuất tiếp theo: ĐỀ XUẤT: chạy sqlmap trên "https://www.google.com/url?sa=E&source=gmail&q=http://testphp.vulnweb.com/page.php?id=1"
HÃY BẮT ĐẦU!

Yêu cầu của người dùng: {input}

{agent_scratchpad} """
agent_system_prompt = PromptTemplate.from_template(agent_system_prompt_template)


# --- PROMPT CHO LUỒNG TRẢ LỜI TRỰC TIẾP TỪ RAG (LUỒNG 1) ---
rag_direct_template = """Nhiệm vụ: Dựa chủ yếu vào thông tin được cung cấp trong "Bối cảnh RAG" dưới đây, hãy trả lời câu hỏi của người dùng một cách trực tiếp và chi tiết.

Yêu cầu của người dùng: {user_input}

Bối cảnh RAG (Thông tin truy xuất từ tài liệu): {rag_context}

Câu trả lời / Mã PoC (Dựa trên RAG): """
rag_direct_prompt = PromptTemplate.from_template(rag_direct_template)

# --- CÁC PROMPT CHO LUỒNG KẾ HOẠCH ĐẦY ĐỦ (FULL PLAN - LUỒNG 2) ---
# --- PROMPT CHO BƯỚC 1: THU THẬP THÔNG TIN ---
recon_template = """ Nhiệm vụ: Với vai trò là một chuyên gia pentest, hãy phân tích yêu cầu sau đây của người dùng. Mục tiêu của bạn là xác định các công nghệ, nền tảng, ngôn ngữ lập trình, và các bề mặt tấn công (attack surfaces) có thể có liên quan đến yêu cầu.

Yêu cầu của người dùng: "{user_input}"

Phân tích của bạn (chỉ tập trung vào công nghệ và bề mặt tấn công): """
recon_prompt = PromptTemplate.from_template(recon_template)

# --- PROMPT CHO BƯỚC 2: MÔ HÌNH HÓA ĐE DỌA & PHÂN TÍCH LỖ HỔNG ---
analysis_template = """ Nhiệm vụ: Dựa trên kết quả phân tích công nghệ và bề mặt tấn công đã cho, hãy liệt kê các loại lỗ hổng bảo mật tiềm tàng và các kịch bản tấn công (attack vectors) khả thi nhất. Hãy sử dụng các tiêu chuẩn như OWASP Top 10 (Web, API, Mobile) làm cơ sở.

Kết quả phân tích công nghệ (Bối cảnh): {recon_results}

Danh sách các lỗ hổng tiềm tàng và kịch bản tấn công (sắp xếp theo mức độ ưu tiên): """
analysis_prompt = PromptTemplate.from_template(analysis_template)

# --- PROMPT CHO BƯỚC 3: XÂY DỰNG KẾ HOẠCH KHAI THÁC ---
exploitation_template = """ Nhiệm vụ: Dựa trên danh sách các lỗ hổng tiềm tàng, hãy xây dựng một kế hoạch hành động chi tiết để kiểm thử và khai thác chúng. Với mỗi lỗ hổng, hãy đề xuất các công cụ, kỹ thuật, và loại payload cụ thể cần sử dụng.

Danh sách lỗ hổng (Bối cảnh): {analysis_results}

Kế hoạch hành động chi tiết (Công cụ, Kỹ thuật, Payload): """
exploitation_prompt = PromptTemplate.from_template(exploitation_template)

# --- PROMPT CHO BƯỚC 4: TẠO PAYLOAD CHI TIẾT DỰA TRÊN RAG (ƯU TIÊN + BỔ SUNG) ---
rag_enhanced_template = """ Nhiệm vụ: Với vai trò là một chuyên gia pentest, hãy tạo ra các payload cụ thể và hướng dẫn chi tiết cách sử dụng chúng. Hãy ưu tiên sử dụng thông tin kỹ thuật tham khảo (RAG) được cung cấp dưới đây làm nền tảng chính.

Bối cảnh:

Kế hoạch tấn công (Tham khảo): {exploitation_results}

Thông tin kỹ thuật tham khảo (Nguồn ưu tiên): {rag_context}

Yêu cầu:

Dựa chủ yếu vào các payload, lệnh, và kỹ thuật trong Thông tin kỹ thuật tham khảo (RAG).

Có thể bổ sung bằng kiến thức chung về pentest, nhưng phải đảm bảo tính liên quan.

Payload chi tiết, các lệnh cần thực thi, và hướng dẫn sử dụng (Ưu tiên RAG): """
rag_enhanced_prompt = PromptTemplate.from_template(rag_enhanced_template)

# --- PROMPT CHO BƯỚC CUỐI CÙNG (FULL PLAN): TẠO POC TỪ RAG ---
poc_generation_template = """ Nhiệm vụ: Với vai trò là một nhà nghiên cứu bảo mật chuyên sâu, hãy phân tích kỹ lưỡng thông tin về CVE hoặc lỗ hổng được cung cấp từ RAG...

Bối cảnh:

Yêu cầu ban đầu của người dùng: {user_input}

Phân tích lỗ hổng & Kịch bản (Tham khảo): {analysis_results}

Kế hoạch khai thác (Tham khảo): {exploitation_results}

Thông tin chi tiết về Lỗ hổng/CVE (Nguồn chính từ RAG): {rag_context}

Payloads gợi ý (Tham khảo): {actionable_intelligence}

Yêu cầu đối với mã PoC:

Xác định rõ mục tiêu: ...

Ngôn ngữ: Ưu tiên Python (dùng requests) hoặc curl.

Rõ ràng & Đơn giản: ...

Giải thích: ...

Tham số hóa: ...

CẢNH BÁO: ...

MÃ PROOF OF CONCEPT (PoC) CHO [Tên Lỗ hổng/CVE]:

Python

# (hoặc curl command)
# ... code PoC ở đây ...
Giải thích mã PoC:

...

Kết quả mong đợi:

...

⚠️ CẢNH BÁO: Mã này chỉ dành cho mục đích giáo dục và kiểm thử bảo mật hợp pháp. """
poc_generation_prompt = PromptTemplate.from_template(poc_generation_template)