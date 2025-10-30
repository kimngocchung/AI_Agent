# File: core/router.py (Phiên bản Router Thông minh - Sửa lỗi Branch)

import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document

# Import các chain con và retriever đã khởi tạo
from .chains.full_plan_chain import full_plan_chain
from .chains.prompts import router_prompt, rag_direct_prompt
from .chains.retriever import retriever # Import retriever đã khởi tạo sẵn

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY không được tìm thấy")

# LLM cho router phân loại (Flash)
router_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash",
                                 google_api_key=api_key)

# LLM cho việc tạo câu trả lời cuối cùng (Pro)
answer_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash",
                           google_api_key=api_key,
                           temperature=0.3)

# Hàm helper để định dạng context từ retriever
def format_docs(docs: list[Document]) -> str:
    if not isinstance(docs, list) or not docs:
        return "Không tìm thấy thông tin liên quan trong cơ sở tri thức."
    top_k_docs = docs[:3]
    return "\n\n---\n\n".join(
        f"Nguồn: {doc.metadata.get('source', 'N/A')}\n\n{doc.page_content}"
        for doc in top_k_docs
    )

# Hàm helper để trích xuất user_input cho các chain con
def prepare_subchain_input(input_dict: dict) -> dict:
    return {"user_input": input_dict["user_input"]}

# Chain RAG Trực tiếp (định nghĩa ở đây để dùng trong branch)
direct_rag_answer_chain = (
    # Nhận input {"user_input": ..., "rag_context": ...}
    rag_direct_prompt
    | answer_llm
    | StrOutputParser()
)

def create_router():
    """
    Tạo Router Chain thông minh: Phân loại -> Kiểm tra RAG -> Chọn Luồng phù hợp.
    """
    # 1. Chain phân loại ý định
    # Input: {"user_input": "..."} -> Output: string (topic)
    classifier_chain = (lambda x: x["user_input"]) | router_prompt | router_llm | StrOutputParser()

    # 2. Chain Lấy Context RAG Sớm
    # Input: {"user_input": "..."} -> Output: list[Document]
    early_rag_retrieval_chain = (lambda x: x["user_input"]) | retriever

    # 3. Logic Phân nhánh Chính (Sửa lỗi ở đây)
    # Input cho branch là dict: {"topic": ..., "user_input": ..., "rag_context_docs": ...}
    branch = RunnableBranch(
        # Điều kiện 1: Intent cụ thể VÀ có context RAG?
        (lambda x: ("specific_vulnerability_info" in x["topic"] or "tool_usage" in x["topic"]) and x.get("rag_context_docs"),
            # Nếu ĐÚNG -> Định dạng context và chạy chain RAG TRỰC TIẾP
            RunnableLambda(
                lambda x: {
                    "user_input": x["user_input"],
                    "rag_context": format_docs(x["rag_context_docs"]) # Định dạng context
                }
            ) | direct_rag_answer_chain
        ),
        # Fallback: Nếu là full plan HOẶC không tìm thấy RAG docs -> chạy full_plan_chain
        RunnableLambda(prepare_subchain_input) | full_plan_chain # full_plan_chain tự query RAG lại
    )

    # 4. Gắn kết tất cả lại
    # - Nhận input {"user_input": "..."}
    # - Chạy classifier lấy "topic"
    # - Chạy retriever sớm lấy "rag_context_docs"
    # - Đưa cả ba vào chain phân nhánh 'branch'
    final_chain = RunnablePassthrough.assign(
        topic=classifier_chain, # Chạy phân loại
        rag_context_docs=early_rag_retrieval_chain # Chạy RAG sớm song song
        # Input gốc ("user_input") được giữ lại tự động bởi RunnablePassthrough
    ) | branch # Đưa dict {"topic": ..., "user_input": ..., "rag_context_docs": ...} vào branch

    return final_chain