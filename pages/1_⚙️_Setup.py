"""
⚙️ Trang Cài đặt & Cấu hình
Cấu hình API keys, Kali Listener và quản lý cơ sở tri thức
"""

import streamlit as st
import os
import sys

# Thêm thư mục cha vào path để import
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.config_manager import (
    save_to_env,
    load_from_env,
    test_gemini_connection,
    test_kali_connection
)
from utils.document_processor import (
    process_pdf,
    process_txt,
    process_docx,
    process_md,
    chunk_documents,
    add_to_faiss,
    get_faiss_stats
)
from utils.url_fetcher import url_to_document
from utils.source_manager import (
    add_source, get_source_count, get_sources_by_type,
    update_source_chunks, delete_source, load_sources,
    update_source_summary
)
from utils.ai_generator import (
    generate_document_summary,
    generate_suggested_questions
)

# Cấu hình trang
st.set_page_config(page_title="Cài đặt - Cyber-Mentor AI", page_icon="⚙️", layout="wide")

st.title("⚙️ Cài đặt & Cấu hình")
st.markdown("Cấu hình hệ thống trước khi sử dụng AI Agent")
st.markdown("---")

# Khởi tạo session state
if "config_saved" not in st.session_state:
    st.session_state.config_saved = False

# ====================
# PHẦN 1: Cấu hình API
# ====================
st.subheader("🔑 Cấu hình API")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Gemini API Key**")
    current_gemini_key = load_from_env("GEMINI_API_KEY")
    gemini_key = st.text_input(
        "Nhập Gemini API key của bạn",
        value=current_gemini_key,
        type="password",
        help="Lấy API key tại https://ai.google.dev/",
        key="gemini_input"
    )
    
    if st.button("💾 Lưu Gemini Key", key="save_gemini"):
        if gemini_key:
            if save_to_env("GEMINI_API_KEY", gemini_key):
                st.success("✅ Đã lưu Gemini API key!")
                st.session_state.config_saved = True
            else:
                st.error("❌ Lưu API key thất bại")
        else:
            st.warning("⚠️ Vui lòng nhập API key")
    
    if gemini_key:
        if st.button("🔌 Kiểm tra kết nối Gemini", key="test_gemini"):
            with st.spinner("Đang kiểm tra kết nối..."):
                success, message = test_gemini_connection(gemini_key)
                if success:
                    st.success(message)
                else:
                    st.error(message)

with col2:
    st.markdown("**Kali Listener URL**")
    current_kali_url = load_from_env("KALI_LISTENER_URL")
    kali_url = st.text_input(
        "Nhập Kali Listener URL",
        value=current_kali_url,
        placeholder="http://192.168.1.100:5000",
        help="URL của Kali Linux API listener",
        key="kali_input"
    )
    
    if st.button("💾 Lưu Kali URL", key="save_kali"):
        if kali_url:
            if save_to_env("KALI_LISTENER_URL", kali_url):
                st.success("✅ Đã lưu Kali Listener URL!")
                st.session_state.config_saved = True
            else:
                st.error("❌ Lưu URL thất bại")
        else:
            st.warning("⚠️ Vui lòng nhập URL")
    
    if kali_url:
        if st.button("🔌 Kiểm tra kết nối Kali", key="test_kali"):
            with st.spinner("Đang kiểm tra kết nối..."):
                success, message = test_kali_connection(kali_url)
                if success:
                    st.success(message)
                else:
                    st.error(message)

st.markdown("---")

# ====================
# PHẦN 2: Quản lý Cơ sở Tri thức
# ====================
st.subheader("📚 Quản lý Cơ sở Tri thức")

# Bộ đếm nguồn
source_count = get_source_count()
st.markdown(f"**Giới hạn nguồn:** {source_count} / 300")

if source_count >= 300:
    st.warning("⚠️ Bạn đã đạt đến giới hạn số lượng nguồn tối đa")

st.markdown("---")

# Các tab upload
tab1, tab2, tab3 = st.tabs(["📤 Tải lên Tệp", "🔗 Dán URL", "📝 Dán Văn bản"])

# TAB 1: Tải lên Tệp
with tab1:
    st.markdown("**Kéo thả hoặc chọn tệp để tải lên**")
    st.caption("Hỗ trợ: PDF, TXT, DOCX, MD, MP3, WAV, JPG, PNG, v.v.")
    
    uploaded_files = st.file_uploader(
        "Chọn tệp",
        type=['pdf', 'txt', 'docx', 'md', 'mp3', 'wav', 'm4a', 'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    
    if uploaded_files:
        st.markdown(f"📄 **{len(uploaded_files)} tệp đã chọn:**")
        for file in uploaded_files:
            st.markdown(f"- `{file.name}` ({file.size} bytes)")
        
        if st.button("➕ Xử lý & Thêm vào Knowledge Base", key="process_files"):
            with st.spinner("Đang xử lý tài liệu..."):
                all_chunks = []
                
                for file in uploaded_files:
                    file_bytes = file.read()
                    file_ext = file.name.split('.')[-1].lower()
                    
                    # Xử lý dựa trên loại file
                    docs = []
                    if file_ext == 'pdf':
                        docs = process_pdf(file_bytes, file.name)
                    elif file_ext == 'txt':
                        docs = process_txt(file_bytes, file.name)
                    elif file_ext == 'docx':
                        docs = process_docx(file_bytes, file.name)
                    elif file_ext == 'md':
                        docs = process_md(file_bytes, file.name)
                    elif file_ext in ['mp3', 'wav', 'm4a']:
                        st.info(f"⏳ Xử lý âm thanh chưa được hỗ trợ: {file.name}")
                        continue
                    elif file_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
                        st.info(f"⏳ Xử lý hình ảnh chưa được hỗ trợ: {file.name}")
                        continue
                    else:
                        st.warning(f"⚠️ Loại tệp không hỗ trợ: {file.name}")
                        continue
                    
                    if docs:
                        # Chunk documents
                        chunks = chunk_documents(docs)
                        all_chunks.extend(chunks)
                        
                        # Tạo tóm tắt và câu hỏi gợi ý
                        full_text = "\n".join([doc.page_content for doc in docs])
                        summary, key_points = generate_document_summary(full_text, file.name)
                        questions = generate_suggested_questions(full_text, file.name)
                        
                        # Thêm vào danh sách nguồn
                        add_source(file.name, file_ext, file.size, summary, questions)
                        update_source_chunks(file.name, len(chunks))
                        
                        st.success(f"✅ {file.name}: {len(chunks)} chunks")
                    else:
                        st.error(f"❌ Xử lý thất bại: {file.name}")
                
                # Thêm vào FAISS
                if all_chunks:
                    st.info(f"Đang thêm tổng cộng {len(all_chunks)} chunks vào FAISS...")
                    faiss_path = "my_faiss_index"
                    success, message = add_to_faiss(all_chunks, faiss_path)
                    
                    if success:
                        st.success(message)
                        st.balloons()
                        st.rerun()

# TAB 2: Dán URL
with tab2:
    st.markdown("**Nhập URL để lấy nội dung từ web**")
    
    url_input = st.text_input(
        "URL",
        placeholder="https://example.com/article",
        label_visibility="collapsed",
        key="url_input"
    )
    
    if st.button("➕ Lấy & Thêm URL", key="process_url"):
        if url_input:
            with st.spinner(f"Đang lấy nội dung từ {url_input}..."):
                success, doc, error = url_to_document(url_input)
                
                if success:
                    # Chunk document
                    chunks = chunk_documents([doc])
                    
                    # Tạo tóm tắt và câu hỏi
                    summary, key_points = generate_document_summary(doc.page_content, url_input)
                    questions = generate_suggested_questions(doc.page_content, url_input)
                    
                    # Thêm vào FAISS
                    faiss_path = "my_faiss_index"
                    add_success, message = add_to_faiss(chunks, faiss_path)
                    
                    if add_success:
                        # Thêm vào danh sách nguồn
                        add_source(url_input, "url", len(doc.page_content), summary, questions)
                        update_source_chunks(url_input, len(chunks))
                        
                        st.success(f"✅ Đã thêm URL: {len(chunks)} chunks")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error(f"❌ {error}")
        else:
            st.warning("⚠️ Vui lòng nhập URL")

# TAB 3: Dán Văn bản
with tab3:
    st.markdown("**Dán văn bản trực tiếp để thêm vào knowledge base**")
    
    text_input = st.text_area(
        "Nội dung văn bản",
        placeholder="Dán văn bản của bạn vào đây...",
        height=200,
        label_visibility="collapsed",
        key="text_input"
    )
    
    text_name = st.text_input("Đặt tên cho văn bản này", placeholder="ví dụ: Ghi chú bảo mật")
    
    if st.button("➕ Thêm Văn bản vào Knowledge Base", key="process_text"):
        if text_input and text_name:
            with st.spinner("Đang xử lý văn bản..."):
                from langchain_core.documents import Document
                
                # Tạo document
                doc = Document(
                    page_content=text_input,
                    metadata={'source': text_name, 'type': 'text'}
                )
                
                # Chunk document
                chunks = chunk_documents([doc])
                
                # Tạo tóm tắt và câu hỏi
                summary, key_points = generate_document_summary(text_input, text_name)
                questions = generate_suggested_questions(text_input, text_name)
                
                # Thêm vào FAISS
                faiss_path = "my_faiss_index"
                success, message = add_to_faiss(chunks, faiss_path)
                
                if success:
                    # Thêm vào danh sách nguồn
                    add_source(text_name, "text", len(text_input), summary, questions)
                    update_source_chunks(text_name, len(chunks))
                    
                    st.success(f"✅ Đã thêm văn bản: {len(chunks)} chunks")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(message)
        else:
            if not text_input:
                st.warning("⚠️ Vui lòng dán nội dung văn bản")
            if not text_name:
                st.warning("⚠️ Vui lòng đặt tên cho văn bản")

st.markdown("---")

# Danh sách nguồn
st.markdown("### 📋 Nguồn Đã Tải Lên")

sources = load_sources()

if sources:
    st.markdown(f"**{len(sources)} nguồn đã tải lên:**")
    
    for idx, source in enumerate(sources):
        with st.expander(f"📄 {source['name']}"):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.caption(f"Loại: {source['type'].upper()} | Chunks: {source['chunks']}")
                if source.get('size', 0) > 0:
                    size_kb = source['size'] / 1024
                    st.caption(f"Kích thước: {size_kb:.1f} KB")
            
            with col3:
                if st.button("🗑️ Xóa", key=f"delete_{idx}"):
                    if delete_source(source['name']):
                        st.success(f"Đã xóa: {source['name']}")
                        st.rerun()
            
            # Hiển thị tóm tắt và câu hỏi (NotebookLM style)
            if source.get('summary'):
                st.markdown("#### 📝 Tóm tắt")
                st.info(source['summary'])
            
            if source.get('suggested_questions'):
                st.markdown("#### 💡 Câu hỏi gợi ý")
                for q in source['suggested_questions']:
                    if st.button(q, key=f"q_{idx}_{q}"):
                        # Logic để chuyển câu hỏi sang trang chat (có thể dùng session state)
                        st.session_state.chat_input_initial = q
                        st.switch_page("app.py")

else:
    st.info("📭 Chưa có nguồn nào được tải lên. Sử dụng các tab ở trên để thêm nguồn!")

st.markdown("---")

# Thống kê Knowledge Base
st.markdown("### 📊 Thống kê Knowledge Base")

faiss_path = "my_faiss_index"
stats = get_faiss_stats(faiss_path)

col1, col2, col3 = st.columns(3)

with col1:
    if stats["exists"]:
        st.metric("Trạng thái", "✅ Hoạt động")
    else:
        st.metric("Trạng thái", "❌ Trống")

with col2:
    st.metric("Tổng số Chunks", stats.get("doc_count", 0))

with col3:
    st.metric("Số lượng Nguồn", len(sources))

st.markdown("---")

# ====================
# PHẦN 3: Trạng thái Hệ thống
# ====================
st.subheader("📊 Trạng thái Hệ thống")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Gemini API**")
    gemini_ok = bool(load_from_env("GEMINI_API_KEY"))
    if gemini_ok:
        st.success("✅ Đã cấu hình")
    else:
        st.error("❌ Chưa cấu hình")

with col2:
    st.markdown("**Kali Listener**")
    kali_ok = bool(load_from_env("KALI_LISTENER_URL"))
    if kali_ok:
        st.success("✅ Đã cấu hình")
    else:
        st.warning("⚠️ Chưa cấu hình")

with col3:
    st.markdown("**FAISS Index**")
    if stats["exists"]:
        st.success(f"✅ {stats['doc_count']} chunks")
    else:
        st.warning("⚠️ Không có dữ liệu")

# Trạng thái sẵn sàng
st.markdown("---")
all_ready = gemini_ok and stats["exists"]

if all_ready:
    st.success("🎉 **Hệ thống đã sẵn sàng!** Bạn có thể bắt đầu sử dụng AI Agent.")
    if st.button("🚀 Đi đến Ứng dụng Chính", type="primary"):
        st.switch_page("app.py")
else:
    st.warning("⚠️ **Hệ thống chưa sẵn sàng.** Vui lòng cấu hình API key và tải lên tài liệu.")
    
    missing = []
    if not gemini_ok:
        missing.append("Gemini API Key")
    if not stats["exists"]:
        missing.append("Knowledge Base (tải lên tài liệu)")
    
    st.markdown(f"**Thiếu:** {', '.join(missing)}")

# Footer
st.markdown("---")
st.markdown("💡 **Mẹo:**")
st.markdown("- Gemini API key là bắt buộc cho các chức năng AI")
st.markdown("- Kali Listener là tùy chọn (chỉ cần cho các công cụ pentesting)")
st.markdown("- Tải lên các tài liệu bảo mật (báo cáo CVE, hướng dẫn khai thác, v.v.) để cải thiện phản hồi của AI")
