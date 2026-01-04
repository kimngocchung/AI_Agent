# File: core/agents/executor.py (Đã cập nhật Burp Tool)

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

# Import các prompt của Agent
from ..chains.prompts import agent_system_prompt_template

# <<< BƯỚC QUAN TRỌNG: IMPORT CÁC TOOL "NÃO-TAY" CỦA BẠN >>>
from ..tools.nmap_tool import run_nmap_scan
from ..tools.sqlmap_tool import run_sqlmap_scan
from ..tools.script_executor_tool import propose_exploit_script
# <<< TOOL MỚI: Tạo script tiên tiến dựa trên Templates + RAG + AI >>>
from ..tools.script_generator_tool import generate_exploit_script, list_available_scripts
# <<< TOOL MỚI: Chạy script cục bộ (không qua Kali) >>>
from ..tools.local_script_runner import run_local_script
# <<< TOOL MỚI: Auto Generate + Run + Fix Loop >>>
from ..tools.auto_script_tool import auto_generate_and_run, list_scripts_for_auto_run
# <<< TOOL MỚI: Static Code Analysis (LUỒNG 4) >>>
from ..tools.code_review_tool import (
    scan_directory_for_code,
    read_source_file,
    scan_hardcoded_credentials,
    scan_idor_vulnerabilities,
    scan_xss_vulnerabilities,
    analyze_security_config,
    full_security_scan,
    import_source_to_rag,  # <<< NEW: Import source code vào RAG
    delete_source_from_rag,  # <<< NEW: Xóa source khỏi RAG
    search_pattern_in_code,  # <<< NEW: Tìm kiếm pattern trong code
    list_imported_projects,  # <<< NEW: Liệt kê projects đã import
)


load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Khởi tạo LLM cho Agent (Dùng model ổn định, không yêu cầu thought_signature)
agent_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash",
                                 google_api_key=api_key,
                                 temperature=0)

# --- ĐỊNH NGHĨA AGENT EXECUTOR ---

def create_agent_executor():
    """
    Tạo một Agent Executor có khả năng gọi các tool pentest.
    """
    
    # Import thêm tool mới
    from core.tools.script_executor_tool import run_script_with_analysis
    
    # 1. Danh sách các tool mà Agent này có thể sử dụng
    tools = [
        run_nmap_scan,
        run_sqlmap_scan,
        propose_exploit_script,  # <<< TOOL: Đề xuất script (cần xác nhận)
        run_script_with_analysis,  # <<< TOOL MỚI: Chạy + phân tích LUÔN (không hỏi, gửi Kali)
        generate_exploit_script,  # <<< TOOL: Tạo/cải tiến script với AI
        list_available_scripts,  # <<< TOOL: Liệt kê scripts và templates
        run_local_script,  # <<< TOOL: Chạy script cục bộ (không qua Kali) để debug/quick test
        # === NEW: Auto Generate + Run + Fix Loop ===
        auto_generate_and_run,  # <<< TOOL: 🔥 TỰ ĐỘNG tạo + chạy + sửa lỗi + phân tích
        list_scripts_for_auto_run,  # <<< TOOL: Liệt kê scripts cho auto run
        # === NEW: Static Code Analysis (LUỒNG 4) ===
        scan_directory_for_code,  # <<< TOOL: Quét thư mục tìm files code
        read_source_file,  # <<< TOOL: Đọc nội dung file source
        scan_hardcoded_credentials,  # <<< TOOL: Tìm passwords, API keys, secrets
        scan_idor_vulnerabilities,  # <<< TOOL: Phát hiện IDOR patterns
        scan_xss_vulnerabilities,  # <<< TOOL: Tìm XSS vulnerabilities
        analyze_security_config,  # <<< TOOL: Phân tích cấu hình bảo mật
        full_security_scan,  # <<< TOOL: 🔥 Full security scan (all-in-one)
        import_source_to_rag,  # <<< TOOL: 🆕 Import source code vào RAG
        delete_source_from_rag,  # <<< TOOL: 🆕 Xóa source khỏi RAG
        search_pattern_in_code,  # <<< TOOL: 🆕 Tìm kiếm pattern trong code
        list_imported_projects,  # <<< TOOL: 🆕 Liệt kê projects đã import
    ]
    
    # 2. Prompt cho Agent - PHẢI DÙNG from_messages với MessagesPlaceholder
    from langchain_core.prompts import MessagesPlaceholder
    
    agent_prompt = ChatPromptTemplate.from_messages([
        ("system", agent_system_prompt_template),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # 3. Tạo Agent
    # bind_tools sẽ tự động "dạy" LLM cách sử dụng các tool của bạn
    agent = create_tool_calling_agent(agent_llm, tools, agent_prompt)
    
    # 4. Tạo Agent Executor
    # Đây là "bộ máy" chạy vòng lặp: Suy nghĩ -> Gọi Tool -> Nhận kết quả -> Suy nghĩ...
    agent_executor_obj = AgentExecutor( # Đổi tên biến để không bị trùng
        agent=agent, 
        tools=tools, 
        verbose=True, # Đặt là True để xem log suy nghĩ của AI
        handle_parsing_errors=True, # Xử lý lỗi nếu AI trả về sai định dạng
        max_iterations=3,  # Giới hạn số vòng lặp để tránh loop vô hạn
        return_intermediate_steps=True  # QUAN TRỌNG: Trả về tool outputs gốc
    )
    
    # Chúng ta bọc nó trong một chain để chuẩn hóa input/output
    # Nó sẽ nhận {"user_input": "...", "rag_context": "...", "chat_history": [...]}
    # Và trả về {"output": "..."}
    
    # Helper function để convert chat_history sang list of BaseMessage
    def convert_chat_history(history):
        """Convert chat history dict/string to list of BaseMessage"""
        from langchain_core.messages import HumanMessage, AIMessage
        
        if not history:
            return []
        
        # Nếu đã là list of messages, return luôn
        if isinstance(history, list) and len(history) > 0:
            if hasattr(history[0], 'content'):
                return history
            
            # Convert từ list of dicts
            messages = []
            for msg in history[-6:]:  # Chỉ lấy 6 tin nhắn gần nhất
                if isinstance(msg, dict):
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))
            return messages
        
        # Nếu là string, return empty list
        return []
    
    # Wrapper để log chi tiết
    def log_agent_execution(result):
        """Log chi tiết kết quả thực thi của Agent"""
        print(f"\n{'='*70}")
        print(f"✅ LUỒNG 3: Agent Executor HOÀN THÀNH")
        print(f"{'─'*70}")
        
        # Log intermediate steps (tool calls)
        steps = result.get("intermediate_steps", [])
        if steps:
            print(f"🔧 TOOLS ĐÃ GỌI: {len(steps)} tool(s)")
            for i, (action, output) in enumerate(steps):
                tool_name = action.tool if hasattr(action, 'tool') else str(action)
                tool_input = str(action.tool_input)[:100] if hasattr(action, 'tool_input') else ""
                output_preview = str(output)[:200] if output else "(không có output)"
                print(f"   └─ [{i+1}] {tool_name}")
                print(f"       Input: {tool_input}...")
                print(f"       Output: {output_preview}...")
        else:
            print(f"🔧 TOOLS ĐÃ GỌI: 0 (Agent trả lời trực tiếp)")
        
        # Log final output
        output = result.get("output", "")
        print(f"{'─'*70}")
        print(f"📤 OUTPUT CUỐI:")
        print(f"   {output[:300]}{'...' if len(output) > 300 else ''}")
        print(f"{'='*70}\n")
        
        return result
    
    agent_executor_chain = (
        RunnablePassthrough.assign(
           # AgentExecutor cần input là "input" và các context khác
           input=lambda x: f"""
**User Request:** {x["user_input"]}

**RAG Context (Script/Tool từ cơ sở tri thức - NẾU CÓ SCRIPT Ở ĐÂY, PHẢI DÙNG NÓ):**
{x.get("rag_context", "Không có context")}
""",
           chat_history=lambda x: convert_chat_history(x.get("chat_history", []))
        )
        | agent_executor_obj
        | RunnableLambda(log_agent_execution)
    )
    
    print("--- [Agent Executor] Đã khởi tạo Luồng 3 (Thực thi Tool) ---")
    return agent_executor_chain

# Khởi tạo agent executor ngay khi load module
agent_executor = create_agent_executor()
