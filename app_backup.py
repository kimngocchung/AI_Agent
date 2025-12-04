# File: app.py (Phiên bản Nâng cấp "Lưu Chat & New Chat & Persistent Storage")

import streamlit as st
from langchain_core.messages import AIMessage
from langchain_core.documents import Document
import os
from dotenv import load_dotenv
import time
import json

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
        # Bỏ st.success đi để đỡ rối giao diện
        # else:
        #     st.success(f"Đã kết nối với Kali Listener tại: {kali_url}")

        print("--- Đang khởi tạo Agent Router 3 Luồng... ---")
        agent = create_router()
        print("--- Agent Router 3 Luồng đã sẵn sàng! ---")
        return agent
    except Exception as e:
        st.error(f"Lỗi khi khởi tạo Agent: {e}")
        st.exception(e)
        st.stop()

agent_chain = load_agent()

# --- ĐƯỜNG DẪN FILE LƯU TRỮ ---
# Hỗ trợ cả Docker và local development
CHAT_HISTORY_DIR = os.getenv("CHAT_HISTORY_DIR", ".")
CHAT_HISTORY_FILE = os.path.join(CHAT_HISTORY_DIR, "chat_history.json")

# --- HÀM LƯU/TẢI LỊCH SỬ CHAT ---
def save_conversations():
    """Lưu tất cả cuộc trò chuyện vào file JSON."""
    try:
        with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'conversations': st.session_state.conversations,
                'active_chat_id': st.session_state.active_chat_id
            }, f, ensure_ascii=False, indent=2)
        print(f"--- Đã lưu {len(st.session_state.conversations)} cuộc trò chuyện vào {CHAT_HISTORY_FILE} ---")
    except Exception as e:
        print(f"--- Lỗi khi lưu lịch sử chat: {e} ---")

def load_conversations():
    """Tải lịch sử cuộc trò chuyện từ file JSON."""
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"--- Đã tải {len(data.get('conversations', {}))} cuộc trò chuyện từ {CHAT_HISTORY_FILE} ---")
                return data.get('conversations', {}), data.get('active_chat_id')
    except Exception as e:
        print(f"--- Lỗi khi tải lịch sử chat: {e} ---")
    return {}, None

# --- QUẢN LÝ SESSION STATE (NÂNG CẤP) ---
def get_current_chat_history():
    """Lấy message list của chat đang active."""
    return st.session_state.conversations[st.session_state.active_chat_id]["messages"]

def get_current_recommendation():
    """Lấy recommendation của chat đang active."""
    return st.session_state.conversations[st.session_state.active_chat_id]["recommendation"]

def set_current_recommendation(value):
    """Set recommendation cho chat đang active."""
    st.session_state.conversations[st.session_state.active_chat_id]["recommendation"] = value

# Khởi tạo cấu trúc state mới
if "conversations" not in st.session_state:
    # Thử tải từ file trước
    loaded_conversations, loaded_active_id = load_conversations()
    
    if loaded_conversations:
        # Nếu có dữ liệu từ file, sử dụng nó
        st.session_state.conversations = loaded_conversations
        st.session_state.active_chat_id = loaded_active_id
    else:
        # Nếu không có, tạo mới
        st.session_state.conversations = {}
        st.session_state.active_chat_id = None

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None

# Nếu chưa có chat nào, tạo chat đầu tiên
if not st.session_state.conversations:
    first_chat_id = f"chat_{int(time.time())}"
    st.session_state.conversations[first_chat_id] = {
        "title": "Cuộc trò chuyện mới",
        "messages": [],
        "recommendation": None
    }
    st.session_state.active_chat_id = first_chat_id
    save_conversations()  # Lưu ngay sau khi tạo

# --- SIDEBAR ---
with st.sidebar:
    st.title("📝 Lịch sử Chat")
    
    if st.button("➕ Trò chuyện mới", use_container_width=True):
        new_chat_id = f"chat_{int(time.time())}"
        st.session_state.conversations[new_chat_id] = {
            "title": "Cuộc trò chuyện mới",
            "messages": [],
            "recommendation": None
        }
        st.session_state.active_chat_id = new_chat_id
        save_conversations()  # Lưu ngay sau khi tạo chat mới
        st.rerun()

    st.divider()

    # Sắp xếp các chat theo thời gian, mới nhất lên trên
    sorted_chat_ids = sorted(st.session_state.conversations.keys(), reverse=True)

    for chat_id in sorted_chat_ids:
        # Tạo 2 cột: cột 1 cho nút chọn chat (80%), cột 2 cho nút xóa (20%)
        col1, col2 = st.columns([0.8, 0.2])
        
        with col1:
            # Nút để chọn chat
            if st.button(st.session_state.conversations[chat_id]["title"], key=f"switch_{chat_id}", use_container_width=True):
                st.session_state.active_chat_id = chat_id
                st.rerun()
        
        with col2:
            # Nút xóa chat
            if st.button("🗑️", key=f"delete_{chat_id}", use_container_width=True):
                # Xóa cuộc trò chuyện
                del st.session_state.conversations[chat_id]
                
                # Nếu đang ở chat vừa xóa, chuyển sang chat khác
                if st.session_state.active_chat_id == chat_id:
                    if st.session_state.conversations:
                        # Chuyển sang chat mới nhất còn lại
                        st.session_state.active_chat_id = sorted(st.session_state.conversations.keys(), reverse=True)[0]
                    else:
                        # Nếu không còn chat nào, tạo chat mới
                        new_chat_id = f"chat_{int(time.time())}"
                        st.session_state.conversations[new_chat_id] = {
                            "title": "Cuộc trò chuyện mới",
                            "messages": [],
                            "recommendation": None
                        }
                        st.session_state.active_chat_id = new_chat_id
                
                save_conversations()  # Lưu ngay sau khi xóa
                st.rerun()

    st.divider()

# --- GIAO DIỆN CHÍNH ---
st.title("🚀 Cyber-Mentor AI Pentesting Agent")
st.caption("AI Co-Pilot: Phân tích, Thực thi và Đề xuất (Human-in-the-Loop)")

# --- 1. HIỂN THỊ LỊCH SỬ CHAT (CỦA PHIÊN HIỆN TẠI) ---
for message in get_current_chat_history():
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 2. LOGIC XỬ LÝ INPUT (QUAN TRỌNG NHẤT) ---
prompt_to_run = None
run_from_button = False

# ƯU TIÊN 1: Kiểm tra xem có Nút "Chấp nhận" không
recommendation = get_current_recommendation()
if recommendation:
    st.info(f"🤖 **Đề xuất tiếp theo:**\n```bash\n{recommendation}\n```")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Chấp nhận Đề xuất", use_container_width=True, type="primary"):
            prompt_to_run = recommendation
            set_current_recommendation(None)
            run_from_button = True
    with col2:
        if st.button("❌ Hủy bỏ", use_container_width=True):
            set_current_recommendation(None)
            st.rerun()

# ƯU TIÊN 2: Nếu không bấm nút, lấy lệnh từ ô chat
if not run_from_button:
    # Kiểm tra xem có input từ trang Setup không
    if "chat_input_initial" in st.session_state and st.session_state.chat_input_initial:
        prompt_to_run = st.session_state.chat_input_initial
        st.session_state.chat_input_initial = None  # Clear sau khi dùng
        set_current_recommendation(None)
    elif new_prompt_from_chat := st.chat_input("Nhập yêu cầu (ví dụ: 'Quét Nmap trang scanme.nmap.org')..."):
        prompt_to_run = new_prompt_from_chat
        set_current_recommendation(None)

# --- 3. BLOCK CHẠY AGENT (CHỈ CHẠY KHI CÓ LỆNH MỚI) ---
if prompt_to_run:
    # Cập nhật tiêu đề cho cuộc trò chuyện nếu đây là tin nhắn đầu tiên
    if not get_current_chat_history():
        st.session_state.conversations[st.session_state.active_chat_id]["title"] = prompt_to_run[:30] + "..."

    # Thêm prompt của user vào history và hiển thị
    get_current_chat_history().append({"role": "user", "content": prompt_to_run})
    save_conversations()  # Lưu ngay sau khi có tin nhắn user
    
    with st.chat_message("user"):
        st.markdown(prompt_to_run)

    # Chạy Agent và hiển thị kết quả
    with st.chat_message("assistant"):
        with st.spinner("Cyber-Mentor đang phân tích..."):
            try:
                print(f"--- Đang gọi Agent 3 Luồng với input: {prompt_to_run} ---")
                # Lấy history của chat hiện tại để đưa vào agent
                current_history = get_current_chat_history()
                response = agent_chain.invoke({
                    "user_input": prompt_to_run,
                    "chat_history": current_history # Thêm history vào
                })
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
                steps_to_display = {
                    "Bước 1: Thu thập thông tin": "recon_results",
                    "Bước 2: Phân tích lỗ hổng": "analysis_results",
                    "Bước 3: Lên kế hoạch khai thác": "exploitation_results",
                    "Bước 4: Tạo Payload (từ RAG)": "actionable_intelligence",
                }
                
                rag_context_str = response.get("rag_context")
                if isinstance(rag_context_str, str) and rag_context_str != "Không tìm thấy thông tin liên quan trong cơ sở tri thức.":
                        st.subheader("📚 Thông tin tham khảo từ RAG:")
                        with st.container(border=True):
                            st.markdown(rag_context_str)
                        st.divider()

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

        
        # --- LOGIC PHÂN TÍCH ĐỀ XUẤT ---
        display_text = full_response_text
        
        if "ĐỀ XUẤT:" in full_response_text:
            try:
                parts = full_response_text.split("ĐỀ XUẤT:", 1)
                display_text = parts[0]
                recommend_cmd = parts[1].strip().strip('`').strip()
                
                if recommend_cmd:
                    new_recommendation = recommend_cmd
            except Exception as e:
                print(f"Lỗi parse đề xuất: {e}")
                display_text = full_response_text

        # HIỂN THỊ NỘI DUNG
        if "Kết quả quét Nmap" in display_text or "Kết quả quét SQLMap" in display_text:
             st.markdown("**Kết quả thực thi:**")
             st.code(display_text, language="bash")
        else:
             st.markdown(display_text)
        
        # LƯU VÀO HISTORY
        get_current_chat_history().append({"role": "assistant", "content": display_text})
        save_conversations()  # Lưu ngay sau khi có tin nhắn mới

        # LƯU ĐỀ XUẤT VÀO STATE
        if new_recommendation:
            set_current_recommendation(new_recommendation)
            st.rerun() 
        
        elif run_from_button:
            st.rerun()