# File: core/router.py (CẬP NHẬT - FIX RAG)

import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document

# Import các chain con và retriever
from .chains.full_plan_chain import full_plan_chain    # LUỒNG 2 (Lên kế hoạch)
from .chains.prompts import router_prompt, rag_direct_prompt
from .chains.retriever import retriever 

# <<< IMPORT LUỒNG MỚI (LUỒNG 3) >>>
from .agents.executor import agent_executor           # LUỒNG 3 (Thực thi)

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
        print("🔴 [RAG DEBUG] Không tìm thấy documents nào!")
        return "Không tìm thấy thông tin liên quan trong cơ sở tri thức."
    
    top_k_docs = docs[:5]  # Lấy top 5 thay vì 3
    
    # === DEBUG LOGGING ===
    print(f"\n{'='*60}")
    print(f"🟢 [RAG DEBUG] Tìm thấy {len(docs)} documents, lấy top {len(top_k_docs)}")
    for i, doc in enumerate(top_k_docs):
        source = doc.metadata.get('source', 'N/A')
        content_preview = doc.page_content[:200].replace('\n', ' ')
        print(f"  📄 Doc {i+1}: {source}")
        print(f"     Preview: {content_preview}...")
    print(f"{'='*60}\n")
    # === END DEBUG ===
    
    return "\n\n---\n\n".join(
        f"Nguồn: {doc.metadata.get('source', 'N/A')}\n\n{doc.page_content}"
        for doc in top_k_docs
    )

# Hàm helper để trích xuất user_input cho các chain con
def prepare_subchain_input(input_dict: dict) -> dict:
    return {"user_input": input_dict["user_input"]}

# Hàm debug để log thông tin phân loại
def log_classification(input_dict: dict) -> dict:
    topic = input_dict.get("topic", "UNKNOWN")
    user_input = input_dict.get("user_input", "")[:50]
    rag_docs = input_dict.get("rag_context_docs", [])
    
    print(f"\n{'='*60}")
    print(f"🔵 [ROUTER DEBUG] Topic: {topic}")
    print(f"   User Input: {user_input}...")
    print(f"   RAG Docs Count: {len(rag_docs) if rag_docs else 0}")
    print(f"{'='*60}\n")
    
    return input_dict

# Helper để check có docs hay không
def has_rag_docs(x):
    docs = x.get("rag_context_docs")
    return docs is not None and len(docs) > 0

# Chain RAG Trực tiếp (LUỒNG 1)
direct_rag_answer_chain = (
    # Nhận input {"user_input": ..., "rag_context": ...}
    rag_direct_prompt
    | answer_llm
    | StrOutputParser()
)

def create_router():
    """
    Tạo Router Chain thông minh: 
    Phân loại -> Kiểm tra RAG -> Chọn 1 trong 3 Luồng.
    """
    
    # 1. Chain phân loại ý định
    # Input: {"user_input": "..."} -> Output: string (topic)
    classifier_chain = (lambda x: x["user_input"]) | router_prompt | router_llm | StrOutputParser()

    # 2. Chain Lấy Context RAG Sớm
    # Input: {"user_input": "..."} -> Output: list[Document]
    early_rag_retrieval_chain = (lambda x: x["user_input"]) | retriever

    # 3. Logic Phân nhánh 3 Luồng (CẬP NHẬT - SỬA LỖI RAG)
    # Input cho branch là dict: {"topic": ..., "user_input": ..., "rag_context_docs": ...}
    branch = RunnableBranch(
        
        # ĐIỀU KIỆN 1: Nếu là yêu cầu THỰC THI (LUỒNG 3)
        # Ưu tiên cao nhất
        (lambda x: "execute_pentest_tool" in x["topic"],
            # Chạy Agent Executor
            RunnableLambda(prepare_subchain_input) | agent_executor
        ),
        
        # ĐIỀU KIỆN 2: Nếu là câu hỏi cụ thể VỀ VULNERABILITY hoặc TOOL (LUỒNG 1)
        # Luôn dùng RAG chain cho các câu hỏi này, có hoặc không có docs
        (lambda x: "specific_vulnerability_info" in x["topic"] or "tool_usage" in x["topic"],
            # Định dạng context và chạy chain RAG TRỰC TIẾP
            RunnableLambda(
                lambda x: {
                    "user_input": x["user_input"],
                    "rag_context": format_docs(x.get("rag_context_docs", []))
                }
            ) | direct_rag_answer_chain
        ),
        
        # FALLBACK: (LUỒNG 2 - Lên kế hoạch)
        # Nếu là 'generate_full_plan' HOẶC các luồng kia không khớp
        RunnableLambda(prepare_subchain_input) | full_plan_chain
    )

    # 4. Gắn kết tất cả lại
    # - Nhận input {"user_input": "..."}
    # - Chạy classifier lấy "topic"
    # - Chạy retriever sớm lấy "rag_context_docs"
    # - Đưa cả ba vào chain phân nhánh 'branch'
    final_chain = RunnablePassthrough.assign(
        topic=classifier_chain,
        rag_context_docs=early_rag_retrieval_chain
    ) | RunnableLambda(log_classification) | branch

    return final_chain