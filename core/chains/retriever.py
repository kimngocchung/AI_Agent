# File: core/chains/retriever.py (Phiên bản với Source Filtering - IMPROVED)

import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.runnables import RunnableLambda

def get_index_path():
    """Trả về đường dẫn tuyệt đối tới FAISS index"""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, 'my_faiss_index')

INDEX_DIRECTORY = get_index_path()

# Biến global để cache
_embeddings = None
_vectorstore = None
_last_doc_count = 0

def get_embeddings():
    """Lazy load embeddings model"""
    global _embeddings
    if _embeddings is None:
        print("--- [RAG] Đang khởi tạo model embedding... ---")
        try:
            # Thử với cấu hình mặc định
            _embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},  # Force CPU để tránh lỗi meta tensor
                encode_kwargs={'normalize_embeddings': True}
            )
            print("--- [RAG] Model embedding đã sẵn sàng! (CPU mode) ---")
        except Exception as e:
            print(f"--- [RAG Error] Lỗi khởi tạo embedding: {e} ---")
            print("--- [RAG] Thử fallback với model đơn giản hơn... ---")
            try:
                # Fallback: dùng model nhẹ hơn
                _embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/paraphrase-MiniLM-L3-v2",
                    model_kwargs={'device': 'cpu'}
                )
                print("--- [RAG] Fallback embedding thành công! ---")
            except Exception as e2:
                print(f"--- [RAG Error] Fallback cũng thất bại: {e2} ---")
                raise
    return _embeddings

def load_vectorstore(force_reload=False):
    """Load hoặc reload vectorstore"""
    global _vectorstore, _last_doc_count
    
    index_path = get_index_path()
    embeddings = get_embeddings()
    
    current_doc_count = 0
    if os.path.exists(index_path):
        try:
            temp_vs = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
            current_doc_count = temp_vs.index.ntotal
        except:
            pass
    
    need_reload = (
        _vectorstore is None or 
        force_reload or 
        current_doc_count != _last_doc_count
    )
    
    if need_reload:
        if current_doc_count != _last_doc_count and _last_doc_count > 0:
            print(f"--- [RAG] Phát hiện thay đổi: {_last_doc_count} -> {current_doc_count} docs ---")
        
        print(f"--- [RAG] Loading vectorstore từ: {index_path} ---")
        
        if not os.path.exists(index_path):
            print(f"--- [RAG Warning] Không tìm thấy index, tạo rỗng ---")
            _vectorstore = FAISS.from_texts(["Chưa có nguồn dữ liệu."], embeddings)
            _last_doc_count = 1
        else:
            try:
                _vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
                _last_doc_count = _vectorstore.index.ntotal
                print(f"--- [RAG] Loaded {_last_doc_count} documents ---")
            except Exception as e:
                print(f"--- [RAG Error] Load failed: {e} ---")
                _vectorstore = FAISS.from_texts(["Lỗi tải index"], embeddings)
                _last_doc_count = 1
    
    return _vectorstore


def normalize_source_name(name: str) -> str:
    """Chuẩn hóa tên nguồn để so sánh"""
    if not name:
        return ""
    # Lấy phần cuối của path/URL nếu có
    name = name.lower().strip()
    # Loại bỏ http/https
    name = name.replace("https://", "").replace("http://", "")
    # Loại bỏ trailing slashes
    name = name.rstrip("/")
    return name


def source_matches(doc_source: str, selected_names: list) -> bool:
    """Kiểm tra xem document source có match với selected sources không"""
    if not selected_names:
        return True  # Không có filter = match tất cả
    
    doc_normalized = normalize_source_name(doc_source)
    
    for sel_name in selected_names:
        sel_normalized = normalize_source_name(sel_name)
        
        # Exact match
        if doc_normalized == sel_normalized:
            return True
        
        # Partial match: kiểm tra doc source có chứa trong selected name hoặc ngược lại
        if doc_normalized and sel_normalized:
            if doc_normalized in sel_normalized or sel_normalized in doc_normalized:
                return True
            
            # Match by basename (for URLs and file paths)
            doc_parts = doc_normalized.split("/")
            sel_parts = sel_normalized.split("/")
            
            # So sánh domain hoặc file basename
            if doc_parts and sel_parts:
                # Nếu doc_source ngắn (như 'cve'), kiểm tra xem nó có trong selected_name
                if len(doc_normalized) < 20:
                    for part in sel_parts:
                        if doc_normalized == part or doc_normalized in part:
                            return True
    
    return False


def extract_cve_from_query(query: str) -> list:
    """Trích xuất CVE IDs từ query"""
    import re
    cve_pattern = re.compile(r'CVE-\d{4}-\d{4,}', re.IGNORECASE)
    return cve_pattern.findall(query.upper())


def retrieve_docs_with_filter(input_data) -> list:
    """
    Retrieve documents với filter theo selected sources.
    Input có thể là string (query) hoặc dict {query, selected_sources}
    """
    # Parse input
    if isinstance(input_data, str):
        query = input_data
        selected_sources = None
    elif isinstance(input_data, dict):
        query = input_data.get("user_input", input_data.get("query", ""))
        selected_sources = input_data.get("selected_sources", None)
    else:
        query = str(input_data)
        selected_sources = None
    
    vs = load_vectorstore()
    
    # 1. TÌM CVE CHÍNH XÁC TRƯỚC (nếu query có CVE ID)
    cve_ids = extract_cve_from_query(query)
    cve_matched_docs = []
    
    if cve_ids:
        # Lấy tất cả documents và tìm exact match CVE
        all_docs = vs.similarity_search(query, k=100)
        
        for doc in all_docs:
            doc_source = doc.metadata.get('source', '').upper()
            doc_content = doc.page_content.upper()[:500]
            
            for cve_id in cve_ids:
                if cve_id in doc_source or cve_id in doc_content:
                    if doc not in cve_matched_docs:
                        cve_matched_docs.append(doc)
    
    # 2. SIMILARITY SEARCH FALLBACK
    k_fetch = 30 if selected_sources else 10
    similarity_docs = vs.similarity_search(query, k=k_fetch)
    
    # 3. MERGE RESULTS: CVE matches first, then similarity
    docs = cve_matched_docs.copy()
    for doc in similarity_docs:
        if doc not in docs:
            docs.append(doc)
    
    # 4. Filter theo selected sources nếu có
    filter_info = ""
    if selected_sources and len(selected_sources) > 0:
        selected_names = [s.get('name', '') for s in selected_sources]
        filter_info = f" (lọc theo {len(selected_names)} nguồn)"
        
        filtered_docs = []
        for doc in docs:
            doc_source = doc.metadata.get('source', '')
            if source_matches(doc_source, selected_names):
                filtered_docs.append(doc)
        
        docs = filtered_docs  # Lấy TẤT CẢ chunks của nguồn đã chọn
        
        if not docs:
            print(f"⚠️ [RAG] Không tìm thấy kết quả cho: \"{query[:40]}...\"{filter_info}")
            return docs
    else:
        docs = docs[:10]  # Nếu không có filter, chỉ lấy top 10
    
    # 5. LOG GỌN GÀNG - chỉ 1 block duy nhất
    source_counts = {}
    for doc in docs:
        source = doc.metadata.get('source', 'N/A')
        short_source = source[:50] if len(source) > 50 else source
        source_counts[short_source] = source_counts.get(short_source, 0) + 1
    
    print(f"📚 [RAG] \"{query[:40]}...\"{filter_info} → {len(docs)} chunks từ {len(source_counts)} nguồn")
    for source, count in source_counts.items():
        print(f"   └─ {source} ({count})")
    
    return docs


def retrieve_docs(query: str) -> list:
    """Hàm retrieve documents cũ - compatibility"""
    return retrieve_docs_with_filter(query)


def reload_retriever():
    """Force reload - gọi sau khi thêm nguồn mới"""
    global _vectorstore, _last_doc_count
    print("--- [RAG] Force reload... ---")
    _vectorstore = None
    _last_doc_count = 0
    load_vectorstore(force_reload=True)

def create_retriever():
    """Tạo retriever object cho LangChain compatibility"""
    vs = load_vectorstore()
    return vs.as_retriever(search_kwargs={"k": 5})

# === EXPORT ===
retriever = RunnableLambda(retrieve_docs_with_filter)