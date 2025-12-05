# File: app.py (NotebookLM-Style với Source Filtering + Chat History + FIXED LAYOUT)

import streamlit as st
from langchain_core.messages import AIMessage
from langchain_core.documents import Document
import os
import sys
from dotenv import load_dotenv
import time
import json

load_dotenv()
sys.path.append(os.path.dirname(__file__))

from core.router import create_router
from utils.source_manager import (
    load_sources, add_source, delete_source, 
    update_source_chunks, update_source_summary, get_source_count
)
from utils.document_processor import (
    process_pdf, process_txt, process_docx, process_md,
    chunk_documents, add_to_faiss, get_faiss_stats
)
from utils.url_fetcher import url_to_document
from utils.ai_generator import generate_document_summary, generate_suggested_questions

# === PAGE CONFIG ===
st.set_page_config(
    page_title="Cyber-Mentor AI",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="auto"  # Tự động hiện sidebar khi có nhiều trang
)

# === LOAD CSS FROM FILE ===
def load_css():
    css_file = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_file):
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ Không tìm thấy file style.css tại: {css_file}")

load_css()


# === AGENT INIT ===
AGENT_VERSION = "v3_source_filter"

@st.cache_resource
def load_agent(_version=AGENT_VERSION):
    print(f"🔄 Loading agent version: {_version}")
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.error("Lỗi: Không tìm thấy GEMINI_API_KEY")
            st.stop()
        agent = create_router()
        return agent
    except Exception as e:
        st.error(f"Lỗi khởi tạo Agent: {e}")
        st.stop()

agent_chain = load_agent()

# === CHAT MANAGEMENT ===
CHAT_HISTORY_DIR = os.getenv("CHAT_HISTORY_DIR", ".")
CHAT_HISTORY_FILE = os.path.join(CHAT_HISTORY_DIR, "chat_history.json")

def save_conversations():
    try:
        with open(CHAT_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'conversations': st.session_state.conversations,
                'active_chat_id': st.session_state.active_chat_id
            }, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Lỗi lưu chat: {e}")

def load_conversations():
    try:
        if os.path.exists(CHAT_HISTORY_FILE):
            with open(CHAT_HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('conversations', {}), data.get('active_chat_id')
    except Exception as e:
        print(f"Lỗi tải chat: {e}")
    return {}, None

def get_current_chat_history():
    return st.session_state.conversations[st.session_state.active_chat_id]["messages"]

def get_current_recommendation():
    return st.session_state.conversations[st.session_state.active_chat_id]["recommendation"]

def set_current_recommendation(value):
    st.session_state.conversations[st.session_state.active_chat_id]["recommendation"] = value

# Session state init
if "conversations" not in st.session_state:
    loaded_conversations, loaded_active_id = load_conversations()
    if loaded_conversations:
        st.session_state.conversations = loaded_conversations
        st.session_state.active_chat_id = loaded_active_id
    else:
        st.session_state.conversations = {}
        st.session_state.active_chat_id = None

if "stop_generation" not in st.session_state:
    st.session_state.stop_generation = False

if not st.session_state.conversations:
    first_chat_id = f"chat_{int(time.time())}"
    st.session_state.conversations[first_chat_id] = {
        "title": "Cuộc trò chuyện mới",
        "messages": [],
        "recommendation": None
    }
    st.session_state.active_chat_id = first_chat_id
    save_conversations()

# === MODAL: ADD SOURCE ===
@st.dialog("Thêm nguồn mới", width="large")
def add_source_modal():
    tab1, tab2, tab3 = st.tabs(["File", "URL", "Text"])
    
    with tab1:
        st.markdown("Tải lên PDF, TXT, DOCX hoặc MD")
        uploaded_files = st.file_uploader(
            "Chọn tệp",
            type=['pdf', 'txt', 'docx', 'md'],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
        
        if uploaded_files and st.button("Thêm", use_container_width=True):
            with st.spinner("Đang xử lý..."):
                for file in uploaded_files:
                    file_bytes = file.read()
                    file_ext = file.name.split('.')[-1].lower()
                    
                    docs = []
                    if file_ext == 'pdf':
                        docs = process_pdf(file_bytes, file.name)
                    elif file_ext == 'txt':
                        docs = process_txt(file_bytes, file.name)
                    elif file_ext == 'docx':
                        docs = process_docx(file_bytes, file.name)
                    elif file_ext == 'md':
                        docs = process_md(file_bytes, file.name)
                    
                    if docs:
                        chunks = chunk_documents(docs)
                        full_text = "\n".join([doc.page_content for doc in docs])
                        summary, _ = generate_document_summary(full_text, file.name)
                        questions = generate_suggested_questions(full_text, file.name)
                        add_source(file.name, file_ext, file.size, summary, questions)
                        update_source_chunks(file.name, len(chunks))
                        add_to_faiss(chunks, "my_faiss_index")
                        st.success(f"✓ {file.name}")
                
                time.sleep(0.5)
                st.rerun()
    
    with tab2:
        st.markdown("Nhập URL")
        url_input = st.text_input("URL", placeholder="https://example.com")
        
        if url_input and st.button("Lấy", use_container_width=True):
            with st.spinner("Đang lấy..."):
                success, doc, error = url_to_document(url_input)
                if success:
                    chunks = chunk_documents([doc])
                    summary, _ = generate_document_summary(doc.page_content, url_input)
                    questions = generate_suggested_questions(doc.page_content, url_input)
                    add_source(url_input, "url", len(doc.page_content), summary, questions)
                    update_source_chunks(url_input, len(chunks))
                    add_to_faiss(chunks, "my_faiss_index")
                    st.success("✓ Đã thêm")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(error)
    
    with tab3:
        st.markdown("Dán văn bản")
        text_input = st.text_area("Nội dung", height=200)
        text_name = st.text_input("Tên", placeholder="ví dụ: Ghi chú")
        
        if text_input and text_name and st.button("Thêm", use_container_width=True):
            with st.spinner("Đang xử lý..."):
                doc = Document(page_content=text_input, metadata={'source': text_name})
                chunks = chunk_documents([doc])
                summary, _ = generate_document_summary(text_input, text_name)
                questions = generate_suggested_questions(text_input, text_name)
                add_source(text_name, "text", len(text_input), summary, questions)
                update_source_chunks(text_name, len(chunks))
                add_to_faiss(chunks, "my_faiss_index")
                st.success("✓ Đã thêm")
                time.sleep(0.5)
                st.rerun()

# ==============================================
# CONTAINER HEIGHT - Điều chỉnh theo màn hình
# ==============================================
CONTAINER_HEIGHT = 550  # Thay đổi giá trị này nếu cần (500-600)

# ==============================================
# MAIN LAYOUT
# ==============================================

col_left, col_center, col_right = st.columns([2.5, 5, 2.5], gap="medium")

# ==============================================
# LEFT: CHAT HISTORY (FIXED LAYOUT)
# ==============================================
with col_left:
    st.markdown("### Lịch sử")
    
    if st.button("Trò chuyện mới", use_container_width=True, type="primary"):
        new_chat_id = f"chat_{int(time.time())}"
        st.session_state.conversations[new_chat_id] = {
            "title": "Cuộc trò chuyện mới",
            "messages": [],
            "recommendation": None
        }
        st.session_state.active_chat_id = new_chat_id
        save_conversations()
        st.rerun()
    
    # === CONTAINER CỐ ĐỊNH CHO LỊCH SỬ ===
    history_container = st.container(height=CONTAINER_HEIGHT)
    with history_container:
        sorted_chats = sorted(st.session_state.conversations.keys(), reverse=True)
        for chat_id in sorted_chats[:15]:  # Tăng lên 15 để có thể scroll
            chat_title = st.session_state.conversations[chat_id]["title"][:25]
            is_active = chat_id == st.session_state.active_chat_id
            
            col_title, col_del = st.columns([4, 1])
            
            with col_title:
                if is_active:
                    st.markdown(f"**→ {chat_title}**")
                else:
                    if st.button(chat_title, key=f"chat_{chat_id}", use_container_width=True):
                        st.session_state.active_chat_id = chat_id
                        st.rerun()
            
            with col_del:
                if st.button("🗑", key=f"del_{chat_id}", help="Xóa"):
                    if len(st.session_state.conversations) > 1:
                        del st.session_state.conversations[chat_id]
                        if is_active:
                            st.session_state.active_chat_id = list(st.session_state.conversations.keys())[0]
                        save_conversations()
                        st.rerun()
                    else:
                        st.toast("Không thể xóa!")

# ==============================================
# CENTER: CHAT (FIXED LAYOUT)
# ==============================================
with col_center:
    # Header đơn giản - chỉ tiêu đề
    st.markdown("### Chat")
    
    # === CONTAINER CỐ ĐỊNH CHO MESSAGES ===
    messages_container = st.container(height=CONTAINER_HEIGHT - 50)
    with messages_container:
        for message in get_current_chat_history():
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
    
    # Recommendation box
    recommendation = get_current_recommendation()
    if recommendation:
        st.info(f"**Đề xuất:** {recommendation}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Chấp nhận", use_container_width=True, key="accept_rec"):
                st.session_state.chat_input_initial = recommendation
                set_current_recommendation(None)
                st.rerun()
        with col2:
            if st.button("Bỏ qua", use_container_width=True, key="skip_rec"):
                set_current_recommendation(None)
                st.rerun()
    
    # === CHAT INPUT + BUTTONS Ở DƯỚI ===
    col_input, col_undo, col_stop = st.columns([8, 1, 1])
    
    with col_input:
        new_prompt = st.chat_input("Nhập câu hỏi...")
    
    with col_undo:
        if st.button("↩️", key="undo_last", help="Undo - Xóa tin nhắn cuối", use_container_width=True):
            history = get_current_chat_history()
            if len(history) >= 2:
                history.pop()
                history.pop()
                save_conversations()
                st.rerun()
            elif len(history) >= 1:
                history.pop()
                save_conversations()
                st.rerun()
    
    with col_stop:
        # Nút Stop - dừng xử lý
        if st.button("⏹️", key="stop_gen", help="Stop - Dừng xử lý", use_container_width=True):
            st.session_state.stop_generation = True
            st.rerun()
    
    prompt_to_run = None
    
    if "chat_input_initial" in st.session_state and st.session_state.chat_input_initial:
        prompt_to_run = st.session_state.chat_input_initial
        st.session_state.chat_input_initial = None
    elif new_prompt:
        prompt_to_run = new_prompt
    
    # Kiểm tra nếu người dùng nhấn Stop
    if st.session_state.get("stop_generation", False):
        st.session_state.stop_generation = False
        prompt_to_run = None
        st.toast("⏹️ Đã dừng xử lý")
    
    if prompt_to_run:
        if not get_current_chat_history():
            st.session_state.conversations[st.session_state.active_chat_id]["title"] = prompt_to_run[:30]
        
        get_current_chat_history().append({"role": "user", "content": prompt_to_run})
        save_conversations()
        
        with messages_container:
            with st.chat_message("user"):
                st.markdown(prompt_to_run)
            
            with st.chat_message("assistant"):
                with st.spinner("Đang phân tích..."):
                    try:
                        # Kiểm tra Stop trước khi gọi API
                        if st.session_state.get("stop_generation", False):
                            st.session_state.stop_generation = False
                            st.warning("⏹️ Đã dừng")
                            st.stop()
                        
                        selected_sources = st.session_state.get("selected_sources", None)
                        
                        response = agent_chain.invoke({
                            "user_input": prompt_to_run,
                            "chat_history": get_current_chat_history(),
                            "selected_sources": selected_sources
                        })
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                        st.stop()
                
                full_response_text = ""
                
                if isinstance(response, dict) and 'actionable_intelligence' in response:
                    full_response_text = response.get('actionable_intelligence', '')
                    if hasattr(full_response_text, 'content'):
                        full_response_text = full_response_text.content
                elif isinstance(response, dict) and 'output' in response:
                    full_response_text = response['output']
                elif isinstance(response, str):
                    full_response_text = response
                else:
                    full_response_text = str(response)
                
                st.markdown(full_response_text)
                
                get_current_chat_history().append({"role": "assistant", "content": full_response_text})
                save_conversations()
                
                if "ĐỀ XUẤT:" in full_response_text:
                    try:
                        parts = full_response_text.split("ĐỀ XUẤT:", 1)
                        recommend_cmd = parts[1].strip().strip('`').strip()
                        if recommend_cmd:
                            set_current_recommendation(recommend_cmd)
                            st.rerun()
                    except:
                        pass

# ==============================================
# RIGHT: SOURCES (FIXED LAYOUT)
# ==============================================
with col_right:
    st.markdown("### Nguồn")
    
    if st.button("Thêm nguồn", use_container_width=True, type="primary"):
        add_source_modal()
    
    sources = load_sources()
    source_count = len(sources)
    faiss_stats = get_faiss_stats("my_faiss_index")
    total_chunks = faiss_stats.get("doc_count", 0)
    
    st.markdown(f"""
    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
        <div class="stat-card" style="flex: 1;">
            <div class="stat-number">{source_count}</div>
            <div class="stat-label">Nguồn</div>
        </div>
        <div class="stat-card" style="flex: 1;">
            <div class="stat-number">{total_chunks}</div>
            <div class="stat-label">Chunks</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # === CONTAINER CỐ ĐỊNH CHO NGUỒN ===
    sources_container = st.container(height=CONTAINER_HEIGHT - 80)  # Trừ đi cho header + stats
    with sources_container:
        if sources:
            select_all = st.checkbox("Chọn tất cả", value=True)
            st.markdown("")
            
            selected_sources = []
            
            for idx, source in enumerate(sources):
                with st.expander(f"{source['name'][:35]}...", expanded=False):
                    is_selected = st.checkbox(
                        "Dùng nguồn này",
                        value=select_all,
                        key=f"src_{idx}",
                        disabled=select_all
                    )
                    
                    if select_all or is_selected:
                        selected_sources.append(source)
                    
                    st.caption(f"Loại: {source['type'].upper()} • Chunks: {source.get('chunks', 0)}")
                    
                    if source.get('summary'):
                        st.markdown("**Tóm tắt:**")
                        st.info(source['summary'][:150] + "..." if len(source.get('summary', '')) > 150 else source.get('summary', ''))
                    
                    st.markdown("")
                    if st.button("Xóa", key=f"delsrc_{idx}", use_container_width=True):
                        delete_source(source['name'])
                        st.rerun()
            
            st.session_state.selected_sources = selected_sources
            
            st.markdown("---")
            st.markdown("### Câu hỏi gợi ý")
            
            if selected_sources:
                all_questions = []
                for source in selected_sources:
                    if source.get('suggested_questions'):
                        for q in source['suggested_questions']:
                            all_questions.append(q)
                
                for idx, q in enumerate(all_questions[:5]):
                    if st.button(q[:60] + "..." if len(q) > 60 else q, key=f"quest_{idx}", use_container_width=True):
                        st.session_state.chat_input_initial = q
                        st.rerun()
            else:
                st.caption("Chọn nguồn để xem câu hỏi")
        else:
            st.info("Chưa có nguồn")
            st.session_state.selected_sources = []