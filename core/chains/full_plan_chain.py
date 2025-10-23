# File: core/chains/full_plan_chain.py (Phiên bản tích hợp RAG thật sự)

from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

# Import các prompt như cũ
from .prompts import (
    recon_prompt,
    analysis_prompt,
    exploitation_prompt,
    rag_enhanced_prompt,
    manual_testing_guide_prompt
)
# IMPORT MỚI: "Người thủ thư" chuyên nghiệp của chúng ta
from .retriever import create_retriever

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY không được tìm thấy")

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.5)

# --- KHỞI TẠO HỆ THỐNG RAG ---
# Dòng này sẽ thực thi toàn bộ logic trong retriever.py để xây dựng CSDL vector
retriever = create_retriever()

# --- Xây dựng các trạm của dây chuyền ---
chain_step1_recon = recon_prompt | llm
chain_step2_analysis = analysis_prompt | llm
chain_step3_exploit_plan = exploitation_prompt | llm
chain_step4_rag_payloads = rag_enhanced_prompt | llm
chain_step5_manual_guide = manual_testing_guide_prompt | llm

# --- Lắp ráp dây chuyền sản xuất cuối cùng ---
full_plan_chain = (
    RunnablePassthrough.assign(
        recon_results=lambda x: chain_step1_recon.invoke({"user_input": x["user_input"]})
    )
    .assign(
        analysis_results=lambda x: chain_step2_analysis.invoke({"recon_results": x["recon_results"]})
    )
    .assign(
        exploitation_results=lambda x: chain_step3_exploit_plan.invoke({"analysis_results": x["analysis_results"]})
    )
    # --- THAY ĐỔI QUAN TRỌNG Ở ĐÂY ---
    # Bỏ hàm giả, dùng retriever thật sự để tìm kiếm dựa trên yêu cầu người dùng
    .assign(
        rag_context=lambda x: retriever.invoke(x["user_input"])
    )
    .assign(
        actionable_intelligence=lambda x: chain_step4_rag_payloads.invoke(x)
    )
    .assign(
        manual_guide=lambda x: chain_step5_manual_guide.invoke(x)
    )
)
