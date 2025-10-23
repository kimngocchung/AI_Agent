# File: core/chains/prompts.py (Phiên bản hoàn chỉnh, ưu tiên RAG + linh hoạt)

from langchain_core.prompts import PromptTemplate

# --- PROMPT CHO BƯỚC 1: THU THẬP THÔNG TIN ---
recon_template = """
**Nhiệm vụ:** Với vai trò là một chuyên gia pentest, hãy phân tích yêu cầu sau đây của người dùng.
Mục tiêu của bạn là xác định các công nghệ, nền tảng, ngôn ngữ lập trình, và các bề mặt tấn công (attack surfaces) có thể có liên quan đến yêu cầu.

**Yêu cầu của người dùng:** "{user_input}"

**Phân tích của bạn (chỉ tập trung vào công nghệ và bề mặt tấn công):**
"""
recon_prompt = PromptTemplate.from_template(recon_template)

# --- PROMPT CHO BƯỚC 2: MÔ HÌNH HÓA ĐE DỌA & PHÂN TÍCH LỖ HỔNG ---
analysis_template = """
**Nhiệm vụ:** Dựa trên kết quả phân tích công nghệ và bề mặt tấn công đã cho, hãy liệt kê các loại lỗ hổng bảo mật tiềm tàng và các kịch bản tấn công (attack vectors) khả thi nhất.
Hãy sử dụng các tiêu chuẩn như OWASP Top 10 (Web, API, Mobile) làm cơ sở.

**Kết quả phân tích công nghệ (Bối cảnh):**
{recon_results}

**Danh sách các lỗ hổng tiềm tàng và kịch bản tấn công (sắp xếp theo mức độ ưu tiên):**
"""
analysis_prompt = PromptTemplate.from_template(analysis_template)

# --- PROMPT CHO BƯỚC 3: XÂY DỰNG KẾ HOẠCH KHAI THÁC ---
exploitation_template = """
**Nhiệm vụ:** Dựa trên danh sách các lỗ hổng tiềm tàng, hãy xây dựng một kế hoạch hành động chi tiết để kiểm thử và khai thác chúng.
Với mỗi lỗ hổng, hãy đề xuất các công cụ, kỹ thuật, và loại payload cụ thể cần sử dụng.

**Danh sách lỗ hổng (Bối cảnh):**
{analysis_results}

**Kế hoạch hành động chi tiết (Công cụ, Kỹ thuật, Payload):**
"""
exploitation_prompt = PromptTemplate.from_template(exploitation_template)

# --- PROMPT CHO BƯỚC 4: TẠO PAYLOAD CHI TIẾT DỰA TRÊN RAG (ƯU TIÊN + BỔ SUNG) ---
rag_enhanced_template = """
**Nhiệm vụ:** Với vai trò là một chuyên gia pentest, hãy tạo ra các payload cụ thể và hướng dẫn chi tiết cách sử dụng chúng. **Hãy ưu tiên sử dụng thông tin kỹ thuật tham khảo (RAG) được cung cấp dưới đây làm nền tảng chính.**

**Bối cảnh:**
- **Kế hoạch tấn công (Tham khảo):** {exploitation_results}
- **Thông tin kỹ thuật tham khảo (Nguồn ưu tiên):**
{rag_context}

**Yêu cầu:**
1.  **Dựa chủ yếu** vào các payload, lệnh, và kỹ thuật trong **Thông tin kỹ thuật tham khảo (RAG)**.
2.  Nếu thông tin RAG chưa đầy đủ hoặc thiếu ví dụ cụ thể cho một điểm nào đó trong kế hoạch tấn công, **có thể bổ sung** bằng kiến thức chung về pentest, nhưng phải đảm bảo tính liên quan.
3.  Trình bày rõ ràng payload, lệnh cần thực thi, và giải thích.

**Payload chi tiết, các lệnh cần thực thi, và hướng dẫn sử dụng (Ưu tiên RAG):**
"""
rag_enhanced_prompt = PromptTemplate.from_template(rag_enhanced_template)

# --- PROMPT CHO BƯỚC CUỐI CÙNG: TẠO HƯỚNG DẪN KIỂM THỬ THỦ CÔNG (ƯU TIÊN RAG + BỔ SUNG) ---
manual_testing_guide_template = """
**Nhiệm vụ:** Với vai trò là một chuyên gia pentest bậc thầy, đang hướng dẫn cho một pentester junior, hãy tạo ra một bản hướng dẫn kiểm thử thủ công (manual testing guide) chi tiết, step-by-step.
**QUAN TRỌNG:** Bản hướng dẫn này phải tập trung **chủ yếu** vào loại lỗ hổng được đề cập trong **Yêu cầu ban đầu của người dùng** VÀ **ưu tiên sử dụng các kỹ thuật, payload cụ thể từ Thông tin kỹ thuật tham khảo (RAG)**.

**Bối cảnh:**
- **Yêu cầu ban đầu của người dùng:** {user_input}
- **Phân tích lỗ hổng & kịch bản tấn công (Tham khảo):** {analysis_results}
- **Kế hoạch khai thác (Tham khảo):** {exploitation_results}
- **Thông tin kỹ thuật tham khảo (Nguồn ưu tiên để tạo hướng dẫn):**
{rag_context}

**Yêu cầu đối với bản hướng dẫn:**
1.  Xác định loại lỗ hổng chính từ **Yêu cầu ban đầu của người dùng**.
2.  Cung cấp các bước thực hiện bằng tay chi tiết **cho loại lỗ hổng chính đó**, **ưu tiên** sử dụng các lệnh và payload được đề cập trong **Thông tin kỹ thuật tham khảo (RAG)**.
3.  Nếu thông tin RAG không đủ chi tiết hoặc thiếu các bước cần thiết, **hãy bổ sung** bằng kiến thức chung về pentest để bản hướng dẫn được hoàn chỉnh và dễ thực hiện, nhưng vẫn phải bám sát vào RAG làm gốc.
4.  Bao gồm các **lệnh terminal cụ thể** và **payload cần thiết** (ưu tiên lấy từ RAG).
5.  Giải thích **kết quả mong đợi** sau mỗi lệnh.
6.  Tập trung vào hướng dẫn thực hành cho lỗ hổng chính, lấy RAG làm nền tảng.

**BẢN HƯỚNG DẪN KIỂM THỬ THỦ CÔNG CHI TIẾT (Tập trung vào: [Loại lỗ hổng từ Yêu cầu ban đầu], Ưu tiên RAG):**
"""
manual_testing_guide_prompt = PromptTemplate.from_template(manual_testing_guide_template)