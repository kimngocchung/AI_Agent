# File: app.py (Cập nhật Tiêu đề Expander)

import streamlit as st
from langchain_core.messages import AIMessage
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
    return create_router()

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
            response = agent_chain.invoke({"user_input": prompt})

        final_content_for_history = ""

        if isinstance(response, dict) and 'manual_guide' in response:
            # <<< THAY ĐỔI TIÊU ĐỀ Ở ĐÂY >>>
            with st.expander("📖 Bản hướng dẫn kiểm thử thủ công chi tiết", expanded=True):
                steps = {
                    "Bước 1: Thu thập thông tin": response.get("recon_results"),
                    "Bước 2: Phân tích lỗ hổng": response.get("analysis_results"),
                    "Bước 3: Lên kế hoạch khai thác": response.get("exploitation_results"),
                    "Bước 4: Tạo Payload (từ RAG)": response.get("actionable_intelligence"),
                    # Bước cuối cùng giờ là bản hướng dẫn chính
                    "Bước 5: Hướng dẫn Chi tiết": response.get("manual_guide"),
                }
                last_step_key = list(steps.keys())[-1]

                for title, content in steps.items():
                    if content and isinstance(content, AIMessage):
                        st.subheader(f"📝 {title}") # Thay đổi icon nếu muốn
                        st.markdown(content.content)
                        st.divider()
                        if title == last_step_key:
                            final_content_for_history = content.content
            
            # Phần hiển thị riêng đã bị xóa

            if final_content_for_history:
                 st.session_state.messages.append({"role": "assistant", "content": final_content_for_history})

        elif isinstance(response, AIMessage):
            st.markdown(response.content)
            final_content_for_history = response.content
            st.session_state.messages.append({"role": "assistant", "content": final_content_for_history})
        
        else:
            final_content_for_history = str(response)
            st.markdown(final_content_for_history)
            st.session_state.messages.append({"role": "assistant", "content": final_content_for_history})