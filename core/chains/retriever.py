# File: core/chains/retriever.py (Phiên bản tải Index có sẵn)

import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Đường dẫn tới thư mục chứa index đã lưu trên máy local
INDEX_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', '..', 'my_faiss_index')

def create_retriever():
    """
    Hàm này tải một FAISS index đã được xây dựng sẵn từ Colab.
    """
    print(f"--- [RAG Local] Đang tải CSDL vector từ: {INDEX_DIRECTORY} ---")

    # Vẫn cần khởi tạo model embedding để FAISS biết cách đọc vector
    try:
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    except Exception as e:
        print(f"--- [RAG Error] Lỗi khi khởi tạo embedding model: {e} ---")
        print("Đảm bảo bạn đã cài đặt các thư viện cần thiết và có kết nối internet (cho lần đầu).")
        raise

    # Tải index từ thư mục đã lưu
    if not os.path.exists(INDEX_DIRECTORY):
        print(f"--- [RAG Error] Không tìm thấy thư mục index tại: '{INDEX_DIRECTORY}' ---")
        print("Hãy chắc chắn bạn đã chạy Colab Notebook, tải index về và đặt đúng vị trí.")
        # Tạo retriever rỗng để tránh lỗi hoàn toàn
        vectorstore = FAISS.from_texts([""], embedding=embeddings)
        return vectorstore.as_retriever()

    try:
        # Quan trọng: Thêm allow_dangerous_deserialization=True
        vectorstore = FAISS.load_local(
            INDEX_DIRECTORY,
            embeddings,
            allow_dangerous_deserialization=True
        )
        print("--- [RAG Local] Đã tải CSDL vector thành công! ---")
        return vectorstore.as_retriever()
    except Exception as e:
        print(f"--- [RAG Error] Không thể tải index từ '{INDEX_DIRECTORY}'. Lỗi: {e} ---")
        # Tạo retriever rỗng
        vectorstore = FAISS.from_texts([""], embedding=embeddings)
        return vectorstore.as_retriever()