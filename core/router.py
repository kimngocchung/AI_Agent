# File: core/router.py (CONTEXT-AWARE ROUTER + QUERY EXPANSION)

import os
import re
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document

# Import các chain con và retriever
from .chains.full_plan_chain import full_plan_chain    # LUỒNG 2 (Lên kế hoạch)
from .chains.prompts import router_prompt, rag_direct_prompt
from .chains.retriever import retrieve_docs_with_filter

# <<< IMPORT LUỒNG MỚI (LUỒNG 3) >>>
from .agents.executor import agent_executor           # LUỒNG 3 (Thực thi)

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY không được tìm thấy")

# LLM cho router phân loại (Flash)
router_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash",
                                  google_api_key=api_key)

# LLM cho việc tạo câu trả lời cuối cùng
answer_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash",
                                  google_api_key=api_key,
                                  temperature=0.3)

# Hàm helper để định dạng context từ retriever
def format_docs(docs: list[Document]) -> str:
    if not isinstance(docs, list) or not docs:
        print("🔴 [RAG DEBUG] Không tìm thấy documents nào!")
        return "Không tìm thấy thông tin liên quan trong cơ sở tri thức."
    
    top_k_docs = docs[:5]
    
    print(f"\n{'='*60}")
    print(f"🟢 [RAG DEBUG] Tìm thấy {len(docs)} documents, lấy top {len(top_k_docs)}")
    for i, doc in enumerate(top_k_docs):
        source = doc.metadata.get('source', 'N/A')
        content_preview = doc.page_content[:200].replace('\n', ' ')
        print(f"  📄 Doc {i+1}: {source}")
        print(f"     Preview: {content_preview}...")
    print(f"{'='*60}\n")
    
    return "\n\n---\n\n".join(
        f"Nguồn: {doc.metadata.get('source', 'N/A')}\n\n{doc.page_content}"
        for doc in top_k_docs
    )

# Hàm helper để format chat history
def format_chat_history(chat_history: list) -> str:
    if not chat_history:
        return "(Không có lịch sử hội thoại)"
    
    # Lấy 6 tin nhắn gần nhất (3 cặp user-assistant)
    recent_messages = chat_history[-6:]
    
    formatted = []
    for msg in recent_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:300]
        if role == "user":
            formatted.append(f"👤 User: {content}")
        elif role == "assistant":
            formatted.append(f"🤖 Assistant: {content}")
    
    return "\n".join(formatted) if formatted else "(Không có lịch sử hội thoại)"

# Hàm trích xuất keywords từ chat history để mở rộng query
def extract_context_keywords(chat_history: list) -> str:
    """
    Trích xuất keywords quan trọng từ chat history gần đây.
    Chỉ thêm context khi thực sự cần thiết (ví dụ: CVE codes, tên tool, target IP...)
    """
    if not chat_history:
        return ""
    
    keywords = []
    
    # Pattern để tìm CVE codes
    cve_pattern = re.compile(r'CVE-\d{4}-\d{4,}', re.IGNORECASE)
    # Pattern để tìm IP addresses
    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    # Pattern để tìm tool names phổ biến
    tool_pattern = re.compile(r'\b(nmap|metasploit|burp|nikto|sqlmap|hydra|john|hashcat|gobuster|dirb|ffuf)\b', re.IGNORECASE)
    
    # Chỉ xem 4 tin nhắn gần nhất
    recent_messages = chat_history[-4:]
    
    for msg in recent_messages:
        content = msg.get("content", "")
        
        # Tìm CVE codes
        cves = cve_pattern.findall(content)
        keywords.extend(cves)
        
        # Tìm IP addresses (chỉ khi có CVE liên quan)
        if cves:
            ips = ip_pattern.findall(content)
            keywords.extend(ips[:1])  # Chỉ lấy 1 IP đầu tiên
        
        # Tìm tool names
        tools = tool_pattern.findall(content)
        keywords.extend(tools)
    
    # Loại bỏ duplicate và giới hạn số lượng
    unique_keywords = list(dict.fromkeys(keywords))[:5]
    
    return " ".join(unique_keywords)

# Hàm chuẩn bị input cho các subchain
def prepare_subchain_input(x: dict) -> dict:
    """
    Chuẩn bị input dict cho các subchain (agent_executor, full_plan_chain).
    """
    return {
        "user_input": x.get("user_input", ""),
        "chat_history": format_chat_history(x.get("chat_history", [])),
        "rag_context": format_docs(x.get("rag_context_docs", [])),
        "selected_sources": x.get("selected_sources", None)
    }

# Hàm debug để log thông tin phân loại
def log_classification(input_dict: dict) -> dict:
    topic = input_dict.get("topic", "UNKNOWN")
    user_input = input_dict.get("user_input", "")[:50]
    rag_docs = input_dict.get("rag_context_docs", [])
    selected_sources = input_dict.get("selected_sources", [])
    
    print(f"\n{'='*60}")
    print(f"🔵 [ROUTER DEBUG] Topic: {topic}")
    print(f"   User Input: {user_input}...")
    print(f"   RAG Docs Count: {len(rag_docs) if rag_docs else 0}")
    print(f"   Selected Sources: {len(selected_sources) if selected_sources else 'All'}")
    print(f"{'='*60}\n")
    
    return input_dict

# Chain RAG Trực tiếp (LUỒNG 1)
direct_rag_answer_chain = (
    rag_direct_prompt
    | answer_llm
    | StrOutputParser()
)

def create_router():
    """
    Tạo Router Chain thông minh: 
    Phân loại -> Kiểm tra RAG -> Chọn 1 trong 3 Luồng.
    """
    
    # 1. Chain phân loại ý định - TRUYỀN CHAT HISTORY ĐỂ HIỂU CONTEXT
    def classify_with_history(x):
        return {
            "user_input": x["user_input"],
            "chat_history": format_chat_history(x.get("chat_history", []))
        }
    
    classifier_chain = RunnableLambda(classify_with_history) | router_prompt | router_llm | StrOutputParser()

    # 2. Chain Lấy Context RAG Sớm - MỞ RỘNG QUERY DỰA TRÊN CHAT HISTORY
    def early_rag_with_filter(x):
        user_input = x["user_input"]
        chat_history = x.get("chat_history", [])
        
        # Trích xuất keywords từ chat history để mở rộng query
        context_keywords = extract_context_keywords(chat_history)
        
        # Nếu có context keywords, thêm vào query
        if context_keywords:
            expanded_query = f"{user_input} {context_keywords}"
            print(f"🔍 [QUERY EXPANSION] Original: '{user_input}' → Expanded: '{expanded_query}'")
        else:
            expanded_query = user_input
        
        return retrieve_docs_with_filter({
            "user_input": expanded_query,
            "selected_sources": x.get("selected_sources", None)
        })
    
    early_rag_retrieval_chain = RunnableLambda(early_rag_with_filter)

    # 3. Logic Phân nhánh 3 Luồng
    branch = RunnableBranch(
        
        # ĐIỀU KIỆN 1: THỰC THI (LUỒNG 3)
        (lambda x: "execute_pentest_tool" in x["topic"],
            RunnableLambda(prepare_subchain_input) | agent_executor
        ),
        
        # ĐIỀU KIỆN 2: VULNERABILITY hoặc TOOL (LUỒNG 1)
        (lambda x: "specific_vulnerability_info" in x["topic"] or "tool_usage" in x["topic"],
            RunnableLambda(
                lambda x: {
                    "user_input": x["user_input"],
                    "rag_context": format_docs(x.get("rag_context_docs", [])),
                    "chat_history": format_chat_history(x.get("chat_history", []))
                }
            ) | direct_rag_answer_chain
        ),
        
        # FALLBACK: (LUỒNG 2 - Lên kế hoạch)
        RunnableLambda(prepare_subchain_input) | full_plan_chain
    )

    # 4. Gắn kết tất cả lại
    final_chain = RunnablePassthrough.assign(
        topic=classifier_chain,
        rag_context_docs=early_rag_retrieval_chain
    ) | RunnableLambda(log_classification) | branch

    return final_chain