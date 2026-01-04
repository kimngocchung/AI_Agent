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

# <<< IMPORT TOOL LOADER >>>
from utils.tool_loader import get_tool_context

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
        return "Không tìm thấy thông tin liên quan trong cơ sở tri thức."
    
    top_k_docs = docs[:5]
    
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
    Bao gồm cả tool context nếu user yêu cầu dùng tool cụ thể.
    """
    user_input = x.get("user_input", "")
    
    # Load tool context nếu user yêu cầu dùng tool cụ thể
    tool_context = get_tool_context(user_input)
    
    # Kết hợp RAG context và tool context
    rag_context = format_docs(x.get("rag_context_docs", []))
    
    if tool_context:
        # Nếu có tool context, đặt lên đầu (ưu tiên cao hơn RAG)
        combined_context = f"{tool_context}\n\n---\n\n**RAG CONTEXT (Thông tin bổ sung):**\n{rag_context}"
    else:
        combined_context = rag_context
    
    return {
        "user_input": user_input,
        "chat_history": x.get("chat_history", []),  # Giữ nguyên list, executor.py sẽ convert
        "rag_context": combined_context,
        "selected_sources": x.get("selected_sources", None)
    }

# Mapping topic -> tên luồng hiển thị
TOPIC_DISPLAY_NAMES = {
    "general_conversation": "LUỒNG 0: Chào Hỏi/Chung",
    "execute_pentest_tool": "LUỒNG 3: Thực Thi Tools",
    "specific_vulnerability_info": "LUỒNG 1: RAG Trả Lời (Lỗ Hổng)",
    "tool_usage": "LUỒNG 1: RAG Trả Lời (Hướng Dẫn Tool)",
    "generate_full_plan": "LUỒNG 2: Lập Kế Hoạch Pentest",
    "static_code_review": "LUỒNG 4: Review Code Tĩnh",
}

# Hàm debug để log thông tin phân loại
def log_classification(input_dict: dict) -> dict:
    topic = input_dict.get("topic", "UNKNOWN").strip().lower()
    user_input = input_dict.get("user_input", "")
    rag_docs = input_dict.get("rag_context_docs", [])
    selected_sources = input_dict.get("selected_sources", [])
    chat_history = input_dict.get("chat_history", [])
    
    # Xác định tên luồng
    flow_name = TOPIC_DISPLAY_NAMES.get(topic, f"UNKNOWN ({topic})")
    
    print(f"\n{'='*70}")
    print(f"📥 USER INPUT: \"{user_input[:100]}{'...' if len(user_input) > 100 else ''}\"")
    print(f"{'='*70}")
    print(f"🔀 ROUTER PHÂN LOẠI:")
    print(f"   └─ Topic: {topic}")
    print(f"   └─ Chuyển đến: {flow_name}")
    print(f"{'─'*70}")
    print(f"📚 CONTEXT:")
    print(f"   └─ RAG Docs: {len(rag_docs) if rag_docs else 0} documents")
    print(f"   └─ Selected Sources: {len(selected_sources) if selected_sources else 'Tất cả'}")
    print(f"   └─ Chat History: {len(chat_history)} tin nhắn")
    print(f"{'─'*70}")
    print(f"⏳ Đang xử lý tại {flow_name}...")
    print(f"{'='*70}\n")
    
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

    # === LOGGING WRAPPERS CHO CÁC LUỒNG ===
    
    def log_general_response(response):
        """Log kết quả Luồng 0 (General Conversation)"""
        print(f"\n{'='*70}")
        print(f"✅ LUỒNG 0: General Conversation HOÀN THÀNH")
        print(f"{'─'*70}")
        print(f"📤 OUTPUT: {response[:200]}...")
        print(f"{'='*70}\n")
        return response
    
    def log_rag_response(response):
        """Log kết quả Luồng 1 (RAG Direct Answer)"""
        print(f"\n{'='*70}")
        print(f"✅ LUỒNG 1: RAG Trả Lời HOÀN THÀNH")
        print(f"{'─'*70}")
        print(f"📤 OUTPUT (preview):")
        print(f"   {response[:300]}{'...' if len(str(response)) > 300 else ''}")
        print(f"{'='*70}\n")
        return response
    
    def log_plan_response(response):
        """Log kết quả Luồng 2 (Full Plan) - CHI TIẾT TỪNG BƯỚC"""
        print(f"\n{'='*70}")
        print(f"✅ LUỒNG 2: Lập Kế Hoạch HOÀN THÀNH")
        print(f"{'='*70}")
        
        if isinstance(response, dict):
            # Các bước chính cần log
            steps_to_log = [
                ("recon_results", "🔍 BƯỚC 1: Thu Thập Thông Tin (Recon)"),
                ("analysis_results", "🔬 BƯỚC 2: Phân Tích Lỗ Hổng"),
                ("exploitation_results", "💥 BƯỚC 3: Kế Hoạch Khai Thác"),
                ("actionable_intelligence", "📋 BƯỚC 4: Payload & Hướng Dẫn"),
            ]
            
            for key, title in steps_to_log:
                value = response.get(key, "")
                if value:
                    # Extract content từ AIMessage nếu cần
                    content = value.content if hasattr(value, 'content') else str(value)
                    
                    print(f"\n{'─'*70}")
                    print(f"{title}")
                    print(f"{'─'*70}")
                    
                    # Giới hạn độ dài để không quá dài
                    if len(content) > 500:
                        print(f"{content[:500]}...")
                        print(f"[...còn {len(content) - 500} ký tự]")
                    else:
                        print(content)
        else:
            print(f"📤 OUTPUT: {str(response)[:500]}...")
        
        print(f"\n{'='*70}\n")
        return response

    # 3. Logic Phân nhánh 3 Luồng
    branch = RunnableBranch(
        
        # ĐIỀU KIỆN 0: GENERAL CONVERSATION (Chào hỏi, câu hỏi chung)
        (lambda x: "general_conversation" in x["topic"].lower(),
            RunnableLambda(lambda x: "Xin chào! 👋 Tôi là Cyber-Mentor, trợ lý AI chuyên về Penetration Testing và An ninh mạng.\n\nTôi có thể giúp bạn:\n- 🔍 Phân tích lỗ hổng và CVE\n- 📋 Lên kế hoạch pentest\n- 🛠️ Sử dụng các công cụ như Nmap, SQLMap\n- 📚 Tìm kiếm thông tin từ cơ sở tri thức\n\nBạn muốn tôi hỗ trợ gì?")
            | RunnableLambda(log_general_response)
        ),
        
        # ĐIỀU KIỆN 1: THỰC THI (LUỒNG 3) - đã có logging trong executor.py
        (lambda x: "execute_pentest_tool" in x["topic"],
            RunnableLambda(prepare_subchain_input) | agent_executor
        ),
        
        # ĐIỀU KIỆN 1.5: STATIC CODE REVIEW (LUỒNG 4) - Review source code
        (lambda x: "static_code_review" in x["topic"],
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
            ) | direct_rag_answer_chain | RunnableLambda(log_rag_response)
        ),
        
        # FALLBACK: (LUỒNG 2 - Lên kế hoạch)
        RunnableLambda(prepare_subchain_input) | full_plan_chain | RunnableLambda(log_plan_response)
    )

    # 4. Gắn kết tất cả lại
    final_chain = RunnablePassthrough.assign(
        topic=classifier_chain,
        rag_context_docs=early_rag_retrieval_chain
    ) | RunnableLambda(log_classification) | branch

    return final_chain