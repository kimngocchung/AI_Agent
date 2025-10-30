# File: app.py (Giữ nguyên - Đã hỗ trợ hiển thị cả 2 loại kết quả)

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
        print("--- Đang khởi tạo Agent Router... ---")
        agent = create_router()
        print("--- Agent Router đã sẵn sàng! ---")
        return agent
    except Exception as e:
        st.error(f"Lỗi khi khởi tạo Agent: {e}")
        st.exception(e)
        st.stop()

agent_chain = load_agent()

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 Cyber-Mentor AI Pentesting Agent")
st.caption("Trợ lý AI chuyên nghiệp cho việc lên kế hoạch và phân tích an ninh mạng")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Nhập yêu cầu của bạn ở đây..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Cyber-Mentor đang phân tích..."):
            try:
                print(f"--- Đang gọi Agent với input: {prompt} ---")
                # Input cho agent luôn là dict {"user_input": prompt}
                response = agent_chain.invoke({"user_input": prompt})
                print(f"--- Agent đã trả về response type: {type(response)} ---")
            except Exception as e:
                st.error(f"Đã xảy ra lỗi khi xử lý yêu cầu: {e}")
                st.exception(e)
                st.stop()

        final_content_for_history = ""

        # --- XỬ LÝ KẾT QUẢ TỪ full_plan_chain (dictionary) ---
        if isinstance(response, dict) and ('actionable_intelligence' in response or 'manual_guide' in response):
            final_step_key = 'actionable_intelligence' if 'actionable_intelligence' in response else 'manual_guide'
            final_step_title = "Payload và Hướng dẫn Chi tiết" if final_step_key == 'actionable_intelligence' else "Hướng dẫn Kiểm thử Thủ công Chi tiết"
            expander_title = f"🔎 Xem Chuỗi tư duy (Kết quả: {final_step_title})"

            with st.expander(expander_title, expanded=True):
                # Hiển thị các bước TRỪ rag_context docs (vì đã được format)
                steps_to_display = {
                    "Bước 1: Thu thập thông tin": "recon_results",
                    "Bước 2: Phân tích lỗ hổng": "analysis_results",
                    "Bước 3: Lên kế hoạch khai thác": "exploitation_results",
                    "Bước 4: Tạo Payload (từ RAG)": "actionable_intelligence",
                    f"Bước 5: {final_step_title}": final_step_key,
                }
                last_step_title = list(steps_to_display.keys())[-1]

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
                        if display_title != last_step_title:
                            st.divider()
                        if display_title == last_step_title:
                            final_content_for_history = content_text

        # --- XỬ LÝ KẾT QUẢ TỪ RAG TRỰC TIẾP (string) ---
        elif isinstance(response, str):
            st.markdown("### 🤖 Phản hồi (Dựa trên RAG):")
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