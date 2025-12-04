# File: core/chains/retriever.py (Phiên bản có thể Reload)

import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.runnables import RunnableLambda

# Đường dẫn chuẩn - dùng biến môi trường hoặc mặc định
def get_index_path():
    """Trả về đường dẫn tuyệt đối tới FAISS index"""
    # Tính từ vị trí file này: core/chains/retriever.py
    # -> lên 2 cấp để về thư mục gốc project
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
    
    # Kiểm tra có cần reload không
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

def retrieve_docs(query: str) -> list:
    """
    Hàm retrieve documents - tự động reload nếu có thay đổi
    """
    vs = load_vectorstore()
    
    print(f"--- [RAG] Searching for: {query[:50]}... ---")
    
    docs = vs.similarity_search(query, k=5)
    
    print(f"--- [RAG] Found {len(docs)} documents ---")
    for i, doc in enumerate(docs[:3]):
        source = doc.metadata.get('source', 'N/A')
        print(f"    {i+1}. {source}")
    
    return docs

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
# Tạo RunnableLambda để dùng trong LangChain chains
retriever = RunnableLambda(retrieve_docs)