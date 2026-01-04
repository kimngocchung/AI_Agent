# File: core/chains/full_plan_chain.py (Phiên bản với CLARIFICATION CHECK)

from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document
import os
from dotenv import load_dotenv

# Import các prompt cho luồng này
from .prompts import (
    recon_prompt,
    analysis_prompt,
    exploitation_prompt,
    rag_enhanced_prompt,

)
# <<< IMPORT retriever ĐÃ KHỞI TẠO SẴN >>>
from .retriever import retriever

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY không được tìm thấy")

# LLM dùng cho các bước của dây chuyền này
llm_plan = ChatGoogleGenerativeAI(model="gemini-2.0-flash",
                           google_api_key=api_key,
                           temperature=0.3)

# Hàm helper để định dạng context từ retriever
def format_docs(docs: list[Document]) -> str:
    if not isinstance(docs, list) or not docs:
        return "Không tìm thấy thông tin liên quan trong cơ sở tri thức."
    return "\n\n---\n\n".join(
        f"Nguồn: {doc.metadata.get('source', 'N/A')}\n\n{doc.page_content}"
        for doc in docs
    )

# Hàm kiểm tra xem recon có yêu cầu làm rõ không
def is_clarification_needed(recon_result) -> bool:
    """Kiểm tra xem kết quả recon có phải là câu hỏi làm rõ không"""
    content = recon_result.content if hasattr(recon_result, 'content') else str(recon_result)
    
    # Các dấu hiệu của câu hỏi làm rõ
    clarification_markers = [
        "cần thêm thông tin",
        "tôi cần thêm",
        "vui lòng cung cấp",
        "bạn có thể cho tôi biết",
        "mục tiêu cụ thể là gì",
        "loại hệ thống",
        "công nghệ sử dụng",
        "phạm vi kiểm thử",
        "ví dụ:",
    ]
    
    content_lower = content.lower()
    return any(marker in content_lower for marker in clarification_markers)

# --- Xây dựng các trạm ---
chain_step1_recon = recon_prompt | llm_plan
chain_step2_analysis = analysis_prompt | llm_plan
chain_step3_exploit_plan = exploitation_prompt | llm_plan
chain_rag_context = retriever | RunnableLambda(format_docs)
chain_step4_rag_payloads = rag_enhanced_prompt | llm_plan


def run_full_plan(input_data: dict) -> dict:
    """
    Chạy full plan chain với logic kiểm tra clarification.
    Nếu step 1 yêu cầu làm rõ → dừng và trả về câu hỏi.
    """
    # Step 1: Recon
    recon_results = chain_step1_recon.invoke({"user_input": input_data["user_input"]})
    
    # Kiểm tra nếu cần làm rõ
    if is_clarification_needed(recon_results):
        print("🔶 [PLAN] Phát hiện yêu cầu chung chung - trả về câu hỏi làm rõ")
        # Trả về chỉ với recon_results (câu hỏi làm rõ)
        return {
            **input_data,
            "recon_results": recon_results,
            "analysis_results": None,
            "exploitation_results": None,
            "actionable_intelligence": recon_results,  # Trả về câu hỏi làm rõ như là kết quả cuối
        }
    
    print("🟢 [PLAN] Yêu cầu đủ chi tiết - tiếp tục lập kế hoạch...")
    
    # Step 2: Analysis
    analysis_results = chain_step2_analysis.invoke({"recon_results": recon_results})
    
    # Step 3: Exploitation Plan
    exploitation_results = chain_step3_exploit_plan.invoke({"analysis_results": analysis_results})
    
    # Step 4: RAG Context + Payloads
    rag_context = chain_rag_context.invoke(input_data["user_input"])
    actionable_intelligence = chain_step4_rag_payloads.invoke({
        "exploitation_results": exploitation_results,
        "rag_context": rag_context
    })
    
    return {
        **input_data,
        "recon_results": recon_results,
        "analysis_results": analysis_results,
        "exploitation_results": exploitation_results,
        "actionable_intelligence": actionable_intelligence,
    }


# --- Full plan chain wrapper ---
full_plan_chain = RunnableLambda(run_full_plan)