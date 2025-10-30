# File: core/chains/full_plan_chain.py (Phiên bản Tạo PoC, dùng retriever chung)

from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document # Import Document
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
llm_plan = ChatGoogleGenerativeAI(model="gemini-2.0-flash", # Hoặc model bạn đang dùng
                           google_api_key=api_key,
                           temperature=0.3) # Giảm temperature

# Hàm helper để định dạng context từ retriever
def format_docs(docs: list[Document]) -> str:
    if not isinstance(docs, list) or not docs:
        return "Không tìm thấy thông tin liên quan trong cơ sở tri thức."
    return "\n\n---\n\n".join(
        f"Nguồn: {doc.metadata.get('source', 'N/A')}\n\n{doc.page_content}"
        for doc in docs
    )

# --- Xây dựng các trạm ---
chain_step1_recon = recon_prompt | llm_plan
chain_step2_analysis = analysis_prompt | llm_plan
chain_step3_exploit_plan = exploitation_prompt | llm_plan
# Bước RAG Context: Lấy input -> Retriever -> Format Docs (Sử dụng retriever chung)
chain_rag_context = retriever | RunnableLambda(format_docs)
chain_step4_rag_payloads = rag_enhanced_prompt | llm_plan


# --- Lắp ráp dây chuyền sản xuất PoC ---
full_plan_chain = (
    RunnablePassthrough.assign(
        recon_results=chain_step1_recon # Input mặc định là {"user_input": "..."}
    )
    .assign(
        analysis_results=lambda x: chain_step2_analysis.invoke({"recon_results": x["recon_results"]})
    )
    .assign(
        exploitation_results=lambda x: chain_step3_exploit_plan.invoke({"analysis_results": x["analysis_results"]})
    )
    .assign( # Chạy bước lấy context RAG, sử dụng input gốc user_input
        rag_context= (lambda x: x["user_input"]) | chain_rag_context
    )
    .assign(
        actionable_intelligence=lambda x: chain_step4_rag_payloads.invoke(
            {
                "exploitation_results": x["exploitation_results"],
                "rag_context": x["rag_context"]
            }
        )
    )

)