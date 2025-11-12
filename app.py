# File: app.py (CẬP NHẬT HOÀN CHỈNH)

import streamlit as st
from langchain_core.messages import AIMessage
from langchain_core.documents import Document # Cần import Document
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

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 Cyber-Mentor AI Pentesting Agent")
st.caption("Trợ lý AI hỗ trợ Lên kế hoạch (Luồng 2), Hỏi đáp RAG (Luồng 1), và Thực thi Tool (Luồng 3)")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Nhập yêu cầu (ví dụ: 'Quét Nmap trang scanme.nmap.org')..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Cyber-Mentor đang phân tích..."):
            try:
                print(f"--- Đang gọi Agent 3 Luồng với input: {prompt} ---")
                # Input cho agent luôn là dict {"user_input": prompt}
                response = agent_chain.invoke({"user_input": prompt})
                print(f"--- Agent đã trả về response type: {type(response)} ---")
                if isinstance(response, dict):
                    print(f"--- Keys: {response.keys()} ---")
            except Exception as e:
                st.error(f"Đã xảy ra lỗi khi xử lý yêu cầu: {e}")
                st.exception(e)
                st.stop()

        final_content_for_history = ""

        # --- XỬ LÝ KẾT QUẢ TỪ LUỒNG 2 (full_plan_chain) ---
        # Output là dict chứa 'actionable_intelligence'
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
                            final_content_for_history = content_text

        # --- XỬ LÝ KẾT QUẢ TỪ LUỒNG 3 (agent_executor) ---
        # Output là dict chứa 'output'
        elif isinstance(response, dict) and 'output' in response:
            st.markdown("### 🤖 Phản hồi (Luồng 3: Thực thi Tool)")
            final_content = response['output']
            
            # Định dạng đặc biệt cho kết quả tool
            if "Kết quả quét Nmap" in final_content or "Kết quả quét SQLMap" in final_content:
                st.markdown("**Đã thực thi tool trên Kali Listener, đây là kết quả:**")
                # Hiển thị kết quả tool trong code block
                st.code(final_content, language="bash") 
                final_content_for_history = f"```bash\n{final_content}\n```"
            else:
                # Nếu là câu trả lời tổng hợp từ Agent
                st.markdown(final_content) 
                final_content_for_history = final_content
            

        # --- XỬ LÝ KẾT QUẢ TỪ LUỒNG 1 (RAG Trực tiếp) ---
        # Output là string
        elif isinstance(response, str):
            st.markdown("### 🤖 Phản hồi (Luồng 1: RAG Hỏi đáp):")
            st.markdown(response)
            final_content_for_history = response

        # --- XỬ LÝ CÁC TRƯỜNG HỢP KHÁC / LỖI ---
        else:
            st.markdown("### ⚠️ Phản hồi không xác định:")
            final_content_for_history = str(response)
            st.markdown(f"```\n{final_content_for_history}\n```")

        # Lưu vào history
        if final_content_for_history:
            st.session_state.messages.append({"role": "assistant", "content": final_content_for_history})