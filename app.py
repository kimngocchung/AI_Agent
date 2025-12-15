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

# --- GIỮ NGUYÊN IMPORTS CỦA BẠN ---
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

# 1. Cấu hình trang
st.set_page_config(layout="wide", page_title="AI-AGent", page_icon="📓")

# 2. Load CSS
def load_css():
    # Đảm bảo bạn đã tạo file assets/style.css với nội dung mới ở trên
    css_file = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_file):
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning(f"⚠️ Không tìm thấy file style.css tại: {css_file}")

load_css()

# === LOGIC AGENT & SESSION STATE (GIỮ NGUYÊN) ===
AGENT_VERSION = "v3_source_filter"

@st.cache_resource
def load_agent(_version=AGENT_VERSION):
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

# === CHAT MANAGEMENT (GIỮ NGUYÊN) ===
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

# Init Session
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

# === MODAL: ADD SOURCE (GIỮ NGUYÊN) ===
@st.dialog("➕ Thêm nguồn mới", width="large")
def add_source_modal():
    tab1, tab2, tab3 = st.tabs(["📄 File", "🌐 URL", "📝 Text"])
    # (Phần logic upload giữ nguyên như code gốc của bạn)
    with tab1:
        st.markdown("Tải lên PDF, TXT, DOCX hoặc MD")
        uploaded_files = st.file_uploader("Chọn tệp", type=['pdf', 'txt', 'docx', 'md'], accept_multiple_files=True, label_visibility="collapsed")
        if uploaded_files and st.button("Thêm File", use_container_width=True, type="primary"):
            with st.spinner("Đang xử lý..."):
                for file in uploaded_files:
                    file_bytes = file.read()
                    file_ext = file.name.split('.')[-1].lower()
                    docs = []
                    if file_ext == 'pdf': docs = process_pdf(file_bytes, file.name)
                    elif file_ext == 'txt': docs = process_txt(file_bytes, file.name)
                    elif file_ext == 'docx': docs = process_docx(file_bytes, file.name)
                    elif file_ext == 'md': docs = process_md(file_bytes, file.name)
                    
                    if docs:
                        chunks = chunk_documents(docs)
                        full_text = "\n".join([doc.page_content for doc in docs])
                        summary, _ = generate_document_summary(full_text, file.name)
                        questions = generate_suggested_questions(full_text, file.name)
                        add_source(file.name, file_ext, file.size, summary, questions)
                        update_source_chunks(file.name, len(chunks))
                        add_to_faiss(chunks, "my_faiss_index")
                        st.success(f"✓ {file.name}")
                time.sleep(0.5); st.rerun()

    with tab2:
        url_input = st.text_input("URL", placeholder="https://example.com")
        if url_input and st.button("Thêm URL", use_container_width=True, type="primary"):
            with st.spinner("Đang tải..."):
                success, doc, error = url_to_document(url_input)
                if success:
                    chunks = chunk_documents([doc])
                    summary, _ = generate_document_summary(doc.page_content, url_input)
                    questions = generate_suggested_questions(doc.page_content, url_input)
                    add_source(url_input, "url", len(doc.page_content), summary, questions)
                    update_source_chunks(url_input, len(chunks))
                    add_to_faiss(chunks, "my_faiss_index")
                    st.success("✓ Đã thêm"); time.sleep(0.5); st.rerun()
                else: st.error(error)

    with tab3:
        text_input = st.text_area("Nội dung", height=200)
        text_name = st.text_input("Tên nguồn", placeholder="Ví dụ: Ghi chú cuộc họp")
        if text_input and text_name and st.button("Thêm Text", use_container_width=True, type="primary"):
            with st.spinner("Đang xử lý..."):
                doc = Document(page_content=text_input, metadata={'source': text_name})
                chunks = chunk_documents([doc])
                summary, _ = generate_document_summary(text_input, text_name)
                questions = generate_suggested_questions(text_input, text_name)
                add_source(text_name, "text", len(text_input), summary, questions)
                update_source_chunks(text_name, len(chunks))
                add_to_faiss(chunks, "my_faiss_index")
                st.success("✓ Đã thêm"); time.sleep(0.5); st.rerun()


# ==============================================================================
# MAIN LAYOUT (THAY ĐỔI LỚN Ở ĐÂY ĐỂ KHỚP UI)
# ==============================================================================

# Header Ẩn (Đã xử lý trong CSS), chúng ta có thể thêm một header giả nếu thích
# c1, c2 = st.columns([0.5, 9.5])
# with c1: st.markdown("## 📓")
# with c2: st.markdown(f"### {st.session_state.conversations[st.session_state.active_chat_id]['title']}")

# Layout 3 cột chính: Trái (1) - Giữa (2.3) - Phải (1)
col_left, col_center, col_right = st.columns([1, 2.3, 1], gap="medium")

# === CỘT TRÁI: QUẢN LÝ NGUỒN ===
with col_left:
    st.markdown('<div class="section-header">📚 Sources</div>', unsafe_allow_html=True)
    
    # Nút thêm nguồn (CSS sẽ làm nó bo tròn)
    if st.button("➕ Add sources", use_container_width=True):
        add_source_modal()
    
    sources = load_sources()
    
    # Stats Row (Hiển thị số liệu đẹp)
    faiss_stats = get_faiss_stats("my_faiss_index")
    total_chunks = faiss_stats.get("doc_count", 0)
    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card"><div class="stat-number">{len(sources)}</div><div class="stat-label">Sources</div></div>
        <div class="stat-card"><div class="stat-number">{total_chunks}</div><div class="stat-label">Chunks</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Danh sách nguồn
    if sources:
        if "selected_sources" not in st.session_state:
            st.session_state.selected_sources = sources
        
        # Select All Checkbox
        select_all = st.checkbox("Select all", value=True)
        selected_sources = []
        
        st.markdown("---")
        for idx, source in enumerate(sources):
            # Chọn icon
            icon = "📄"
            if source['type'] == 'url': icon = "🌐"
            elif source['type'] == 'text': icon = "📝"
            
            # Expander cho từng nguồn
            with st.expander(f"{icon} {source['name']}", expanded=False):
                is_selected = st.checkbox("Use this source", value=select_all, key=f"src_{idx}", disabled=select_all)
                if select_all or is_selected:
                    selected_sources.append(source)
                
                st.caption(f"Type: {source['type'].upper()}")
                if st.button("🗑️ Delete", key=f"delsrc_{idx}"):
                    delete_source(source['name'])
                    st.rerun()
                    
        st.session_state.selected_sources = selected_sources
    else:
        st.info("Chưa có nguồn nào. Hãy thêm nguồn mới!")
        st.session_state.selected_sources = []

# === CỘT GIỮA: CHAT CHÍNH ===
with col_center:
    # Header Chat
    chat_title = st.session_state.conversations[st.session_state.active_chat_id]["title"]
    st.markdown(f'<div class="section-header">💬 {chat_title}</div>', unsafe_allow_html=True)
    
    # Messages Container
    # Lưu ý: height=600 để chat box dài ra, style.css sẽ làm nó bo tròn
    chat_container = st.container(height=600)
    with chat_container:
        chat_history = get_current_chat_history()
        if not chat_history:
            st.markdown("""
            <div style="text-align: center; color: #888; padding: 40px;">
                <h3>👋 Welcome Pentest AI</h3>
                <p>Bắt đầu bằng cách hỏi câu hỏi dựa trên tài liệu của bạn.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            for message in chat_history:
                avatar = "👤" if message["role"] == "user" else "✨"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

    # Recommendation Box (Gợi ý từ AI)
    recommendation = get_current_recommendation()
    if recommendation:
        st.info(f"💡 **AI Đề xuất:** {recommendation}")
        r1, r2 = st.columns(2)
        if r1.button("✅ Đồng ý", key="acc_rec", use_container_width=True):
            st.session_state.chat_input_initial = recommendation
            set_current_recommendation(None)
            st.rerun()
        if r2.button("❌ Bỏ qua", key="skip_rec", use_container_width=True):
            set_current_recommendation(None)
            st.rerun()

    # Input Area & Buttons
    # Chia cột để input và nút nằm cùng hàng
    col_in, col_act = st.columns([6, 1])
    with col_in:
        prompt = st.chat_input("Nhập câu hỏi của bạn...")
    
    with col_act:
        # Nút Undo hoặc Stop
        if st.button("↩️", help="Undo last", use_container_width=True):
             history = get_current_chat_history()
             if history:
                 history.pop(); history.pop() if len(history) > 0 else None
                 save_conversations(); st.rerun()

    # Xử lý Logic Chat (Giữ nguyên logic của bạn)
    prompt_to_run = None
    if "chat_input_initial" in st.session_state and st.session_state.chat_input_initial:
        prompt_to_run = st.session_state.chat_input_initial
        st.session_state.chat_input_initial = None
    elif prompt:
        prompt_to_run = prompt

    if prompt_to_run:
        # 1. Lưu tin nhắn User
        get_current_chat_history().append({"role": "user", "content": prompt_to_run})
        save_conversations()
        
        # 2. Hiển thị ngay lập tức
        with chat_container:
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt_to_run)
            
            with st.chat_message("assistant", avatar="✨"):
                with st.spinner("AI đang suy nghĩ..."):
                    try:
                        selected_sources = st.session_state.get("selected_sources", None)
                        # GỌI AGENT
                        response = agent_chain.invoke({
                            "user_input": prompt_to_run,
                            "chat_history": get_current_chat_history(),
                            "selected_sources": selected_sources
                        })
                        
                        # Xử lý kết quả trả về
                        full_text = ""
                        if isinstance(response, dict) and 'actionable_intelligence' in response:
                            full_text = response['actionable_intelligence']
                            if hasattr(full_text, 'content'): full_text = full_text.content
                        elif isinstance(response, str):
                            full_text = response
                        else:
                            full_text = str(response)

                        st.markdown(full_text)
                        
                        # Lưu tin nhắn Bot
                        get_current_chat_history().append({"role": "assistant", "content": full_text})
                        save_conversations()
                        
                        # Xử lý đề xuất (nếu có)
                        if "ĐỀ XUẤT:" in full_text:
                            parts = full_text.split("ĐỀ XUẤT:", 1)
                            set_current_recommendation(parts[1].strip())
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

# === CỘT PHẢI: STUDIO & HISTORY ===
with col_right:
    st.markdown('<div class="section-header">✨ Studio</div>', unsafe_allow_html=True)
    
    # Studio Grid (Dùng HTML để đẹp như Google)
    st.markdown("""
    <div class="studio-grid">
        <div class="studio-item bg-blue"><div class="s-icon">🎧</div><div class="s-label">Audio</div></div>
        <div class="studio-item bg-purple"><div class="s-icon">🧠</div><div class="s-label">Mind Map</div></div>
        <div class="studio-item bg-orange"><div class="s-icon">🎴</div><div class="s-label">Flashcards</div></div>
        <div class="studio-item bg-green"><div class="s-icon">❓</div><div class="s-label">Quiz</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # History Section
    st.markdown('<div class="section-header">📜 History</div>', unsafe_allow_html=True)
    
    if st.button("➕ New Conversation", use_container_width=True, type="primary"):
        new_id = f"chat_{int(time.time())}"
        st.session_state.conversations[new_id] = {"title": "New conversation", "messages": [], "recommendation": None}
        st.session_state.active_chat_id = new_id
        save_conversations(); st.rerun()
        
    sorted_chats = sorted(st.session_state.conversations.keys(), reverse=True)[:8]
    for cid in sorted_chats:
        c_title = st.session_state.conversations[cid]["title"][:20]
        is_active = (cid == st.session_state.active_chat_id)
        
        c1, c2 = st.columns([4, 1])
        if c1.button(f"{'📍' if is_active else '💬'} {c_title}", key=f"c_{cid}", use_container_width=True):
            st.session_state.active_chat_id = cid
            st.rerun()
        if c2.button("🗑️", key=f"d_{cid}"):
            if len(st.session_state.conversations) > 1:
                del st.session_state.conversations[cid]
                if is_active: st.session_state.active_chat_id = list(st.session_state.conversations.keys())[0]
                save_conversations(); st.rerun()

    # Suggested Questions (Lấy từ Sources)
    st.markdown("---")
    st.markdown('<div class="section-header">💡 Suggested</div>', unsafe_allow_html=True)
    selected_sources = st.session_state.get("selected_sources", [])
    if selected_sources:
        q_count = 0
        for src in selected_sources:
            if src.get('suggested_questions'):
                for q in src['suggested_questions']:
                    if q_count < 3:
                        if st.button(f"❓ {q[:40]}...", key=f"sq_{q_count}", use_container_width=True, help=q):
                            st.session_state.chat_input_initial = q
                            st.rerun()
                        q_count += 1