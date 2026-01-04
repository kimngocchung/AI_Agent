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
import google.generativeai as genai


def generate_conversation_title(first_message: str) -> str:
    """
    Tự động tạo tiêu đề ngắn gọn cho cuộc hội thoại dựa trên tin nhắn đầu tiên.
    Giống như Gemini/Claude auto-rename conversations.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or len(first_message.strip()) < 3:
            return first_message[:30] + "..." if len(first_message) > 30 else first_message
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""Tạo một tiêu đề NGẮN GỌN (tối đa 5-7 từ) cho cuộc hội thoại dựa trên tin nhắn sau.
Chỉ trả về tiêu đề, không giải thích gì thêm.

Tin nhắn: {first_message[:200]}

Tiêu đề:"""
        
        response = model.generate_content(prompt)
        title = response.text.strip().strip('"').strip("'")
        
        # Giới hạn độ dài
        if len(title) > 40:
            title = title[:37] + "..."
        
        return title if title else first_message[:30]
        
    except Exception as e:
        print(f"Error generating title: {e}")
        # Fallback: dùng tin nhắn đầu tiên
        return first_message[:30] + "..." if len(first_message) > 30 else first_message

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
    
    # === PHẦN SCRIPTS (Tách riêng khỏi RAG) ===
    st.markdown("---")
    st.markdown('<div class="section-header">🛠️ Scripts</div>', unsafe_allow_html=True)
    st.caption("Scripts được load nguyên vẹn (không qua RAG chunking)")
    
    # Script Upload
    uploaded_script = st.file_uploader(
        "Upload Script (.py, .sh)", 
        type=["py", "sh", "bash"],
        key="script_uploader",
        help="Scripts sẽ được lưu vào folder scripts/ và AI có thể sử dụng trực tiếp"
    )
    
    if uploaded_script:
        scripts_dir = os.path.join(os.path.dirname(__file__), "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        
        script_path = os.path.join(scripts_dir, uploaded_script.name)
        with open(script_path, 'wb') as f:
            f.write(uploaded_script.getvalue())
        st.success(f"✅ Đã lưu: {uploaded_script.name}")
        st.rerun()
    
    # Hiển thị danh sách scripts hiện có
    scripts_dir = os.path.join(os.path.dirname(__file__), "scripts")
    if os.path.exists(scripts_dir):
        scripts = [f for f in os.listdir(scripts_dir) if f.endswith(('.py', '.sh', '.bash'))]
        if scripts:
            for script in scripts:
                script_icon = "🐍" if script.endswith('.py') else "📜"
                with st.expander(f"{script_icon} {script}", expanded=False):
                    script_path = os.path.join(scripts_dir, script)
                    # Hiển thị info
                    file_size = os.path.getsize(script_path)
                    with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = len(f.readlines())
                    st.caption(f"📏 {lines} dòng | 💾 {file_size/1024:.1f} KB")
                    
                    # Nút xóa
                    if st.button("🗑️ Xóa", key=f"del_script_{script}"):
                        os.remove(script_path)
                        st.success(f"Đã xóa {script}")
                        st.rerun()
        else:
            st.caption("Chưa có script nào.")

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
        # === CHECK CONFIRMATION WORDS - XỬ LÝ TRƯỚC KHI GỌI AGENT ===
        confirmation_words = ["có", "yes", "ok", "đồng ý", "chạy", "confirm", "thực hiện", "chạy đi", "run"]
        is_confirmation = prompt_to_run.lower().strip() in confirmation_words
        
        # Nếu là confirmation và có pending script trong session state
        if is_confirmation and "pending_script" in st.session_state and st.session_state.pending_script:
            # Lưu tin nhắn user
            get_current_chat_history().append({"role": "user", "content": prompt_to_run})
            save_conversations()
            
            # Chạy script luôn mà không cần gọi LLM
            with chat_container:
                with st.chat_message("user", avatar="👤"):
                    st.markdown(prompt_to_run)
                
                with st.chat_message("assistant", avatar="✨"):
                    st.markdown("✅ Đã nhận xác nhận. Đang thực thi script trên Kali...")
                    
                    try:
                        from core.tools.script_executor_tool import execute_script_on_kali
                        
                        script_data = st.session_state.pending_script
                        
                        # Lấy args từ proposal (AI Agent tự điền)
                        args = script_data.get("args", "")
                        target = script_data.get("target", "")
                        
                        print(f"[APP DEBUG] Executing script with target: {target}")
                        print(f"[APP DEBUG] Args from proposal: {args}")
                        
                        result = execute_script_on_kali(
                            script_content=script_data.get("script", ""),
                            script_type=script_data.get("type", "python"),
                            args=args
                        )
                        
                        output_text = result.get("output", "").strip()
                        error_text = result.get("error_output", "").strip()
                        
                        # Debug: hiển thị raw result
                        print(f"[APP DEBUG] Result success: {result.get('success')}")
                        print(f"[APP DEBUG] Output length: {len(output_text)}")
                        print(f"[APP DEBUG] Error length: {len(error_text)}")
                        print(f"[APP DEBUG] Output preview: {output_text[:500] if output_text else 'EMPTY'}")
                        
                        if result.get("success"):
                            st.success("✅ Script chạy thành công!")
                            if output_text:
                                st.markdown("**📄 Output:**")
                                # Giới hạn output để tránh UI crash
                                display_output = output_text[:10000] if len(output_text) > 10000 else output_text
                                st.markdown(f"```bash\n{display_output}\n```")
                            else:
                                st.warning("⚠️ Script chạy thành công nhưng không có output. Có thể script cần thêm target URL.")
                        else:
                            st.error("❌ Script thất bại!")
                            if error_text:
                                st.markdown(f"```\n{error_text}\n```")
                            if output_text:
                                st.markdown("**Output trước khi lỗi:**")
                                st.markdown(f"```\n{output_text}\n```")
                        
                        # Lưu kết quả
                        result_msg = f"## 🖥️ Kết quả\n**Trạng thái:** {'✅ Thành công' if result.get('success') else '❌ Thất bại'}\n```\n{output_text or error_text or '(Không có output)'}\n```"
                        get_current_chat_history().append({"role": "assistant", "content": result_msg})
                        save_conversations()
                        
                        # Xóa pending script
                        del st.session_state["pending_script"]
                        
                        # === AI PHÂN TÍCH KẾT QUẢ ===
                        if output_text and len(output_text) > 50:  # Chỉ phân tích nếu có output đáng kể
                            st.markdown("---")
                            with st.spinner("🧠 AI đang phân tích kết quả..."):
                                try:
                                    from langchain_google_genai import ChatGoogleGenerativeAI
                                    import os
                                    
                                    analysis_llm = ChatGoogleGenerativeAI(
                                        model="gemini-2.0-flash",
                                        google_api_key=os.getenv("GEMINI_API_KEY"),
                                        temperature=0.3
                                    )
                                    
                                    analysis_prompt = f"""Bạn là chuyên gia phân tích bảo mật. Phân tích kết quả scan sau đây và đưa ra:

1. **TÓM TẮT:** Kết quả chính (vulnerable hay không?)
2. **CHI TIẾT:** Giải thích ý nghĩa của từng phần output
3. **KHUYẾN NGHỊ:** Bước tiếp theo nên làm gì?

**OUTPUT TỪ SCRIPT:**
```
{output_text[:3000]}
```

Trả lời ngắn gọn, dễ hiểu, bằng tiếng Việt."""

                                    analysis_response = analysis_llm.invoke(analysis_prompt)
                                    analysis_text = analysis_response.content if hasattr(analysis_response, 'content') else str(analysis_response)
                                    
                                    st.markdown("### 🧠 Phân tích của AI:")
                                    st.markdown(analysis_text)
                                    
                                    # Lưu phân tích vào chat history
                                    get_current_chat_history().append({
                                        "role": "assistant", 
                                        "content": f"### 🧠 Phân tích kết quả:\n{analysis_text}"
                                    })
                                    save_conversations()
                                    
                                except Exception as e:
                                    st.warning(f"⚠️ Không thể phân tích tự động: {e}")
                        
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                        if "pending_script" in st.session_state:
                            del st.session_state["pending_script"]
            
            # Không gọi agent, kết thúc luôn
            st.stop()
        
        # 1. Lưu tin nhắn User
        get_current_chat_history().append({"role": "user", "content": prompt_to_run})
        save_conversations()
        
        # === AUTO-RENAME: Đổi title nếu đây là tin nhắn đầu tiên ===
        current_title = st.session_state.conversations[st.session_state.active_chat_id].get("title", "")
        if len(get_current_chat_history()) == 1 and current_title in ["Cuộc trò chuyện mới", "New conversation"]:
            new_title = generate_conversation_title(prompt_to_run)
            st.session_state.conversations[st.session_state.active_chat_id]["title"] = new_title
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
                        
                        # Debug: Print raw response
                        print(f"[APP DEBUG] Raw response type: {type(response)}")
                        print(f"[APP DEBUG] Raw response keys: {response.keys() if isinstance(response, dict) else 'N/A'}")
                        
                        # === QUAN TRỌNG: Lấy tool output từ intermediate_steps ===
                        # Tìm tool output có nội dung chi tiết (run_script_with_analysis hoặc propose_exploit_script)
                        detailed_tool_output = ""
                        if isinstance(response, dict) and 'intermediate_steps' in response:
                            for i, step in enumerate(response['intermediate_steps']):
                                if hasattr(step, '__iter__') and len(step) > 1:
                                    step_output = str(step[1]) if len(step) > 1 else ""
                                    print(f"[APP DEBUG] Step {i} output length: {len(step_output)}")
                                    
                                    # Lấy output từ run_script_with_analysis (có ## 📄 Script) hoặc propose_exploit_script (có __SCRIPT_PROPOSAL__)
                                    if "## 📄 Script:" in step_output or "### 🔍 Phân tích Script:" in step_output:
                                        detailed_tool_output = step_output
                                        print(f"[APP DEBUG] ✅ Found run_script_with_analysis output!")
                                        break
                                    elif "__SCRIPT_PROPOSAL__" in step_output:
                                        detailed_tool_output = step_output
                                        print(f"[APP DEBUG] ✅ Found SCRIPT_PROPOSAL in intermediate_steps!")
                                        break
                        
                        # Xử lý kết quả trả về - hỗ trợ nhiều format
                        full_text = ""
                        
                        if isinstance(response, dict):
                            # Print first 500 chars of output for debugging
                            raw_output = response.get('output', '')
                            print(f"[APP DEBUG] Output preview: {str(raw_output)[:500]}")
                            
                            # ƯU TIÊN: Nếu có detailed tool output, dùng nó thay vì AI summary
                            if detailed_tool_output:
                                full_text = detailed_tool_output
                                print(f"[APP DEBUG] Using detailed_tool_output instead of AI summary")
                            elif 'output' in response:
                                full_text = response['output']
                            elif 'actionable_intelligence' in response:
                                full_text = response['actionable_intelligence']
                            elif 'result' in response:
                                full_text = response['result']
                            elif 'content' in response:
                                full_text = response['content']
                            else:
                                # Fallback: format dict đẹp hơn thay vì raw
                                import json
                                full_text = f"```json\n{json.dumps(response, ensure_ascii=False, indent=2)}\n```"
                        elif isinstance(response, str):
                            full_text = response
                        elif hasattr(response, 'content'):
                            full_text = response.content
                        else:
                            full_text = str(response)
                        
                        # Đảm bảo full_text là string
                        if hasattr(full_text, 'content'):
                            full_text = full_text.content
                        if not isinstance(full_text, str):
                            full_text = str(full_text)

                        st.markdown(full_text)
                        
                        # === XỬ LÝ SCRIPT PROPOSAL ===
                        # Detect marker đặc biệt __SCRIPT_PROPOSAL__
                        print(f"[APP DEBUG] Checking for SCRIPT_PROPOSAL markers...")
                        print(f"[APP DEBUG] Has __SCRIPT_PROPOSAL__: {'__SCRIPT_PROPOSAL__' in full_text}")
                        print(f"[APP DEBUG] Has __END_SCRIPT_PROPOSAL__: {'__END_SCRIPT_PROPOSAL__' in full_text}")
                        
                        if "__SCRIPT_PROPOSAL__" in full_text and "__END_SCRIPT_PROPOSAL__" in full_text:
                            import re
                            import json as json_module
                            
                            print("[APP DEBUG] Found both markers! Extracting JSON...")
                            
                            # Pattern để lấy JSON giữa 2 markers (hỗ trợ multi-line)
                            match = re.search(r'__SCRIPT_PROPOSAL__\s*(\{[\s\S]*?\})\s*__END_SCRIPT_PROPOSAL__', full_text)
                            if match:
                                try:
                                    json_str = match.group(1).strip()
                                    print(f"[APP DEBUG] JSON string length: {len(json_str)}")
                                    print(f"[APP DEBUG] JSON first 200 chars: {json_str[:200]}")
                                    
                                    # Parse JSON bằng ast.literal_eval để xử lý Python string escaping
                                    import ast
                                    script_data = ast.literal_eval(json_str)
                                    st.session_state["pending_script"] = script_data
                                    st.success("✅ **Script đã sẵn sàng!** Trả lời 'có' hoặc click nút bên dưới để chạy trên Kali.")
                                    print(f"[APP DEBUG] ✅ SUCCESS! Parsed script proposal:")
                                    print(f"    type={script_data.get('type')}")
                                    print(f"    target={script_data.get('target')}")
                                    print(f"    script length={len(script_data.get('script', ''))}")
                                except Exception as e:
                                    print(f"[APP DEBUG] ❌ Error parsing with ast: {e}")
                                    # Fallback: try eval
                                    try:
                                        script_data = eval(json_str)
                                        st.session_state["pending_script"] = script_data
                                        st.success("✅ **Script đã sẵn sàng!** Trả lời 'có' để chạy.")
                                        print(f"[APP DEBUG] ✅ SUCCESS with eval fallback")
                                    except Exception as e2:
                                        print(f"[APP DEBUG] ❌ Eval also failed: {e2}")
                                        st.warning(f"⚠️ Không thể parse script proposal: {e}")
                            else:
                                print("[APP DEBUG] ❌ Regex match failed - no match found")
                        
                        # Cách 2: Detect code blocks Python/Bash + từ khóa xác nhận
                        elif ("```python" in full_text or "```bash" in full_text) and \
                             any(kw in full_text.lower() for kw in ["xác nhận", "đồng ý", "có muốn", "bạn có muốn", "yes", "có"]):
                            import re
                            
                            # Trích xuất code block
                            code_match = re.search(r'```(python|bash)\n(.*?)```', full_text, re.DOTALL)
                            if code_match:
                                script_type = code_match.group(1)
                                script_content = code_match.group(2).strip()
                                
                                # Tìm target URL nếu có
                                target_match = re.search(r'(https?://[^\s\'"]+)', full_text)
                                target = target_match.group(1) if target_match else "Unknown"
                                
                                st.session_state["pending_script"] = {
                                    "type": script_type,
                                    "script": script_content,
                                    "description": "Script từ AI response",
                                    "target": target
                                }
                                st.success(f"✅ Đã nhận diện script {script_type.upper()}. Trả lời **'có'** để chạy trên Kali.")
                        
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

# === XỬ LÝ NÚT XÁC NHẬN SCRIPT ===
if "pending_script" in st.session_state and st.session_state.pending_script:
    script_data = st.session_state.pending_script
    
    with st.container():
        st.markdown("---")
        st.markdown("### 🔐 Script đang chờ xác nhận")
        st.markdown(f"**Loại:** `{script_data.get('type', 'python')}`")
        st.markdown(f"**Mô tả:** {script_data.get('description', 'N/A')}")
        st.markdown(f"**Mục tiêu:** {script_data.get('target', 'N/A')}")
        
        col_run, col_cancel = st.columns(2)
        
        with col_run:
            if st.button("✅ Chạy trên Kali", type="primary", use_container_width=True):
                with st.spinner("Đang chạy script trên Kali..."):
                    try:
                        from core.tools.script_executor_tool import execute_script_on_kali
                        
                        # Lấy args từ proposal (AI Agent tự điền)
                        args = script_data.get("args", "")
                        target = script_data.get("target", "")
                        
                        print(f"[APP DEBUG] Sidebar execute - Target: {target}, Args: {args}")
                        
                        result = execute_script_on_kali(
                            script_content=script_data.get("script", ""),
                            script_type=script_data.get("type", "python"),
                            args=args
                        )
                        
                        # Hiển thị kết quả
                        output_text = result.get("output", "").strip()
                        error_text = result.get("error_output", "").strip()
                        
                        if result.get("success"):
                            st.success("✅ Script chạy thành công!")
                            if output_text:
                                st.markdown("**📄 Output:**")
                                # Dùng markdown code block để format terminal output
                                st.markdown(f"```bash\n{output_text}\n```")
                        else:
                            st.error("❌ Script thất bại!")
                            if error_text:
                                st.markdown("**⚠️ Error:**")
                                st.markdown(f"```\n{error_text}\n```")
                            if output_text:
                                st.markdown("**📄 Output:**")
                                st.markdown(f"```\n{output_text}\n```")
                        
                        # Lưu kết quả vào chat history - format đẹp hơn
                        result_text = f"""## 🖥️ Kết quả chạy script

**Trạng thái:** {"✅ Thành công" if result.get("success") else "❌ Thất bại"}

### 📄 Output:
```bash
{output_text if output_text else "(Không có output)"}
```

### ⚠️ Error Log:
```
{error_text if error_text else "(Không có lỗi)"}
```
"""
                        get_current_chat_history().append({"role": "assistant", "content": result_text})
                        save_conversations()
                        
                        # Xóa pending script
                        del st.session_state["pending_script"]
                        
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
                        if "pending_script" in st.session_state:
                            del st.session_state["pending_script"]
        
        with col_cancel:
            if st.button("❌ Hủy", use_container_width=True):
                del st.session_state["pending_script"]
                st.info("Đã hủy chạy script.")
                st.rerun()

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