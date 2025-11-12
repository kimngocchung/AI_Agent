# File: app.py (Phiên bản Nâng cấp "Human-in-the-Loop" - ĐẦY ĐỦ)

import streamlit as st
from langchain_core.messages import AIMessage
from langchain_core.documents import Document 
import os
from dotenv import load_dotenv

# --- LOAD ENV FIRST ---
load_dotenv()

# --- IMPORT AGENT SAU KHI LOAD ENV ---
from core.router import create_router

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(
    page_title="Cyber-Mentor AI",
    page_icon="🚀",
    layout="wide"
)

# --- KHỞI TẠO AGENT ---
@st.cache_resource
def load_agent():
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("Lỗi: Không tìm thấy GEMINI_API_KEY trong file .env!")
            st.stop()
        
        kali_url = os.getenv("KALI_LISTENER_URL")
        if not kali_url:
            st.warning("Cảnh báo: Không tìm thấy KALI_LISTENER_URL. Các tool (Nmap, SQLMap) sẽ không hoạt động.")
        else:
            st.success(f"Đã kết nối với Kali Listener tại: {kali_url}")

        print("--- Đang khởi tạo Agent Router 3 Luồng... ---")
        agent = create_router()
        print("--- Agent Router 3 Luồng đã sẵn sàng! ---")
        return agent
    except Exception as e:
        st.error(f"Lỗi khi khởi tạo Agent: {e}")
        st.exception(e)
        st.stop()

agent_chain = load_agent()

# --- QUẢN LÝ SESSION STATE (BỘ NHỚ CỦA APP) ---
# 1. 'messages' lưu toàn bộ lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = []
# 2. 'recommendation' lưu đề xuất tiếp theo của AI
if "recommendation" not in st.session_state:
    st.session_state.recommendation = None

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 Cyber-Mentor AI Pentesting Agent")
st.caption("AI Co-Pilot: Phân tích, Thực thi và Đề xuất (Human-in-the-Loop)")

# --- 1. HIỂN THỊ LỊCH SỬ CHAT (TỪ BỘ NHỚ) ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 2. LOGIC XỬ LÝ INPUT (QUAN TRỌNG NHẤT) ---

# Biến 'prompt' sẽ lưu lệnh cần chạy.
# Nó có thể đến từ 2 nguồn: Nút "Chấp nhận" hoặc Ô "Chat Input"
prompt_to_run = None
run_from_button = False

# ƯU TIÊN 1: Kiểm tra xem có Nút "Chấp nhận" không
if st.session_state.recommendation:
    # Hiển thị thông báo đề xuất
    st.info(f"🤖 **Đề xuất tiếp theo:**\n```bash\n{st.session_state.recommendation}\n```")
    
    # Chia cột cho 2 nút
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Chấp nhận Đề xuất", use_container_width=True, type="primary"):
            prompt_to_run = st.session_state.recommendation
            st.session_state.recommendation = None # Xóa đề xuất sau khi chấp nhận
            run_from_button = True
    with col2:
        if st.button("❌ Hủy bỏ", use_container_width=True):
            st.session_state.recommendation = None
            st.rerun() # Chạy lại script để xóa nút

# ƯU TIÊN 2: Nếu không bấm nút, lấy lệnh từ ô chat
if not run_from_button:
    if new_prompt_from_chat := st.chat_input("Nhập yêu cầu (ví dụ: 'Quét Nmap trang scanme.nmap.org')..."):
        prompt_to_run = new_prompt_from_chat
        st.session_state.recommendation = None # Xóa đề xuất cũ (nếu có) khi gõ lệnh mới

# --- 3. BLOCK CHẠY AGENT (CHỈ CHẠY KHI CÓ LỆNH MỚI) ---
if prompt_to_run:
    # Thêm prompt của user vào history và hiển thị
    st.session_state.messages.append({"role": "user", "content": prompt_to_run})
    with st.chat_message("user"):
        st.markdown(prompt_to_run)

    # Chạy Agent và hiển thị kết quả
    with st.chat_message("assistant"):
        with st.spinner("Cyber-Mentor đang phân tích..."):
            try:
                print(f"--- Đang gọi Agent 3 Luồng với input: {prompt_to_run} ---")
                response = agent_chain.invoke({"user_input": prompt_to_run})
                print(f"--- Agent đã trả về response type: {type(response)} ---")
                if isinstance(response, dict):
                    print(f"--- Keys: {response.keys()} ---")
            except Exception as e:
                st.error(f"Đã xảy ra lỗi khi xử lý yêu cầu: {e}")
                st.exception(e)
                st.stop()

        # --- Xử lý và Phân tích Response ---
        full_response_text = ""
        new_recommendation = None

        # --- XỬ LÝ KẾT QUẢ TỪ LUỒNG 2 (full_plan_chain) ---
        if isinstance(response, dict) and 'actionable_intelligence' in response:
            st.markdown("### 🤖 Phản hồi (Luồng 2: Lên Kế hoạch)")
            
            final_step_key = 'actionable_intelligence'
            final_step_title = "Payload và Hướng dẫn Chi tiết"
            expander_title = f"🔎 Xem Chuỗi tư duy (Luồng 2: {final_step_title})"

            with st.expander(expander_title, expanded=True):
                # Hiển thị các bước TRỪ rag_context docs
                steps_to_display = {
                    "Bước 1: Thu thập thông tin": "recon_results",
                    "Bước 2: Phân tích lỗ hổng": "analysis_results",
                    "Bước 3: Lên kế hoạch khai thác": "exploitation_results",
                    "Bước 4: Tạo Payload (từ RAG)": "actionable_intelligence",
                }
                
                # Hiển thị RAG Context (đã được format thành string trong chain)
                rag_context_str = response.get("rag_context")
                if isinstance(rag_context_str, str) and rag_context_str != "Không tìm thấy thông tin liên quan trong cơ sở tri thức.":
                        st.subheader("📚 Thông tin tham khảo từ RAG:")
                        with st.container(border=True):
                            st.markdown(rag_context_str)
                        st.divider()

                # Hiển thị các bước còn lại
                for display_title, response_key in steps_to_display.items():
                    content = response.get(response_key)
                    content_text = ""
                    if isinstance(content, AIMessage):
                        content_text = content.content
                    elif isinstance(content, str):
                        content_text = content
                    elif content is not None:
                        content_text = str(content)

                    if content_text:
                        st.subheader(f"📝 {display_title}")
                        st.markdown(content_text)
                        if response_key != final_step_key:
                            st.divider()
                        else:
                            # Đây là nội dung cuối cùng để lưu vào history
                            full_response_text = content_text


        # --- XỬ LÝ KẾT QUẢ TỪ LUỒNG 3 (agent_executor) ---
        elif isinstance(response, dict) and 'output' in response:
            st.markdown("### 🤖 Phản hồi (Luồng 3: Thực thi Tool)")
            full_response_text = response['output']

        # --- XỬ LÝ KẾT QUẢ TỪ LUỒNG 1 (RAG Trực tiếp) ---
        elif isinstance(response, str):
            st.markdown("### 🤖 Phản hồi (Luồng 1: RAG Hỏi đáp):")
            full_response_text = response

        # --- XỬ LÝ CÁC TRƯỜNG HỢP KHÁC / LỖI ---
        else:
            st.markdown("### ⚠️ Phản hồi không xác định:")
            full_response_text = str(response)

        
        # --- LOGIC PHÂN TÍCH ĐỀ XUẤT (MỚI) ---
        display_text = full_response_text # Mặc định hiển thị toàn bộ
        
        # Kiểm tra xem AI có trả về ĐỀ XUẤT không
        if "ĐỀ XUẤT:" in full_response_text:
            try:
                # Tách response thành 2 phần: Phân tích và Đề xuất
                parts = full_response_text.split("ĐỀ XUẤT:", 1)
                display_text = parts[0] # Phần phân tích (trước chữ ĐỀ XUẤT)
                
                # Lấy lệnh đề xuất và làm sạch (xóa backtick, whitespace)
                recommend_cmd = parts[1].strip().strip('`').strip()
                
                if recommend_cmd: # Đảm bảo không rỗng
                    new_recommendation = recommend_cmd
            except Exception as e:
                print(f"Lỗi parse đề xuất: {e}")
                # Nếu lỗi, cứ hiển thị text gốc
                display_text = full_response_text

        # 4. HIỂN THỊ NỘI DUNG (Phần Phân tích)
        # (Lưu ý: Logic hiển thị tool output trong code block đã được gộp vào đây)
        if "Kết quả quét Nmap" in display_text or "Kết quả quét SQLMap" in display_text:
             st.markdown("**Kết quả thực thi:**")
             st.code(display_text, language="bash")
        else:
             st.markdown(display_text) # Hiển thị phân tích hoặc RAG
        
        # 5. LƯU VÀO HISTORY (Chỉ lưu phần đã hiển thị)
        st.session_state.messages.append({"role": "assistant", "content": display_text})

        # 6. LƯU ĐỀ XUẤT VÀO STATE ĐỂ HIỂN THỊ NÚT
        if new_recommendation:
            st.session_state.recommendation = new_recommendation
            # Tự động chạy lại script để hiển thị nút "Accept" ngay lập tức
            st.rerun() 
        
        # Nếu chạy từ nút bấm và không có đề xuất mới -> rerun để dọn dẹp
        elif run_from_button:
            st.rerun()