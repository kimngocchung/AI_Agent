# File: core/chains/retriever.py (Phiên bản tải Index có sẵn)

import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# Đường dẫn tới thư mục chứa index đã lưu trên máy local
INDEX_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', '..', 'my_faiss_index')

# Khởi tạo embedding model một lần duy nhất khi module được load
try:
    print("--- [RAG Global] Đang khởi tạo model embedding (chỉ một lần)... ---")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    print("--- [RAG Global] Model embedding đã sẵn sàng! ---")
except Exception as e:
    print(f"--- [RAG Error] Lỗi nghiêm trọng khi khởi tạo embedding model: {e} ---")
    embeddings = None

def create_retriever():
    """
    Hàm này tải một FAISS index đã được xây dựng sẵn từ Colab.
    Sử dụng embedding model đã được khởi tạo sẵn.
    """
    global embeddings

    if embeddings is None:
        print("--- [RAG Error] Embedding model chưa được khởi tạo thành công. Không thể tải index. ---")
        try:
             embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
             print("--- [RAG Retry] Khởi tạo lại embedding model thành công. ---")
        except Exception as retry_e:
             print(f"--- [RAG Error] Khởi tạo lại embedding model thất bại: {retry_e} ---")
             # Cố gắng tạo retriever rỗng nếu không thể load model
             try:
                 temp_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2") # Tạo lại instance tạm
                 vectorstore = FAISS.from_texts(["Lỗi embedding model"], temp_embeddings)
                 return vectorstore.as_retriever()
             except Exception: # Nếu vẫn lỗi thì chịu
                 print("--- [RAG FATAL] Không thể tạo retriever rỗng. ---")
                 raise # Ném lỗi ra ngoài


    print(f"--- [RAG Local] Đang tải CSDL vector từ: {INDEX_DIRECTORY} ---")

    if not os.path.exists(INDEX_DIRECTORY) or not os.path.isdir(INDEX_DIRECTORY):
        print(f"--- [RAG Error] Không tìm thấy thư mục index hợp lệ tại: '{INDEX_DIRECTORY}' ---")
        print("Hãy chắc chắn bạn đã chạy Colab Notebook, tải index về và đặt đúng vị trí.")
        vectorstore = FAISS.from_texts(["Index không tồn tại"], embeddings)
        return vectorstore.as_retriever()

    try:
        vectorstore = FAISS.load_local(
            INDEX_DIRECTORY,
            embeddings,
            allow_dangerous_deserialization=True
        )
        print("--- [RAG Local] Đã tải CSDL vector thành công! ---")
        return vectorstore.as_retriever()
    except FileNotFoundError:
         print(f"--- [RAG Error] Không tìm thấy file index.faiss hoặc index.pkl trong '{INDEX_DIRECTORY}'.")
    except Exception as e:
        print(f"--- [RAG Error] Không thể tải index từ '{INDEX_DIRECTORY}'. Lỗi: {e} ---")

    print("--- [RAG Warning] Tạo retriever rỗng do lỗi tải index. ---")
    vectorstore = FAISS.from_texts(["Lỗi tải index"], embeddings)
    return vectorstore.as_retriever()

# Khởi tạo retriever ngay khi module được import để cache lại
retriever = create_retriever()