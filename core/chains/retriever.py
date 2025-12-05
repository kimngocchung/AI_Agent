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
            _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            print("--- [RAG] Model embedding đã sẵn sàng! ---")
        except Exception as e:
            print(f"--- [RAG Error] Lỗi khởi tạo embedding: {e} ---")
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
    
    print(f"--- [RAG] Searching for: {query[:50]}... ---")
    
    # Lấy nhiều hơn nếu cần filter
    k_fetch = 30 if selected_sources else 5
    docs = vs.similarity_search(query, k=k_fetch)
    
    # Filter theo selected sources nếu có
    if selected_sources and len(selected_sources) > 0:
        selected_names = [s.get('name', '') for s in selected_sources]
        
        print(f"--- [RAG] Filtering by {len(selected_names)} selected sources ---")
        for name in selected_names:
            print(f"    ✓ Selected: {name[:60]}")
        
        # Filter docs
        filtered_docs = []
        rejected_docs = []
        
        for doc in docs:
            doc_source = doc.metadata.get('source', '')
            
            if source_matches(doc_source, selected_names):
                filtered_docs.append(doc)
                print(f"    ✅ MATCH: {doc_source[:60]}")
            else:
                rejected_docs.append(doc_source)
        
        # Log rejected docs for debugging
        if rejected_docs:
            print(f"    ❌ REJECTED {len(rejected_docs)} docs:")
            for rej in rejected_docs[:3]:
                print(f"       - {rej[:60]}")
        
        docs = filtered_docs[:5]  # Lấy top 5 sau khi filter
        print(f"--- [RAG] After filter: {len(docs)} documents ---")
        
        # Nếu không có docs match, log warning
        if not docs:
            print("--- [RAG WARNING] Không có document nào match với selected sources! ---")
    else:
        docs = docs[:5]
        print(f"--- [RAG] No filter applied, using all sources ---")
    
    print(f"--- [RAG] Found {len(docs)} documents ---")
    for i, doc in enumerate(docs[:5]):
        source = doc.metadata.get('source', 'N/A')
        print(f"    {i+1}. {source[:80]}")
    
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