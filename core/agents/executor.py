# File: core/agents/executor.py (Đã cập nhật Burp Tool)

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

# Import các prompt của Agent
from ..chains.prompts import agent_system_prompt_template

# <<< BƯỚC QUAN TRỌNG: IMPORT CÁC TOOL "NÃO-TAY" CỦA BẠN >>>
from ..tools.nmap_tool import run_nmap_scan
from ..tools.sqlmap_tool import run_sqlmap_scan


load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Khởi tạo LLM cho Agent (Nên dùng model mạnh một chút)
agent_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", # Nâng cấp lên Pro nếu cần
                                 google_api_key=api_key,
                                 temperature=0)

# --- ĐỊNH NGHĨA AGENT EXECUTOR ---

def create_agent_executor():
    """
    Tạo một Agent Executor có khả năng gọi các tool pentest.
    """
    
    # 1. Danh sách các tool mà Agent này có thể sử dụng
    tools = [
        run_nmap_scan,
        run_sqlmap_scan,
    ]
    
    # 2. Prompt cho Agent
    # Chúng ta dùng prompt từ file prompts.py
    agent_prompt = ChatPromptTemplate.from_template(agent_system_prompt_template)
    
    # 3. Tạo Agent
    # bind_tools sẽ tự động "dạy" LLM cách sử dụng các tool của bạn
    agent = create_tool_calling_agent(agent_llm, tools, agent_prompt)
    
    # 4. Tạo Agent Executor
    # Đây là "bộ máy" chạy vòng lặp: Suy nghĩ -> Gọi Tool -> Nhận kết quả -> Suy nghĩ...
    agent_executor_obj = AgentExecutor( # Đổi tên biến để không bị trùng
        agent=agent, 
        tools=tools, 
        verbose=True, # Đặt là True để xem log suy nghĩ của AI
        handle_parsing_errors=True # Xử lý lỗi nếu AI trả về sai định dạng
    )
    
    # Chúng ta bọc nó trong một chain để chuẩn hóa input/output
    # Nó sẽ nhận {"user_input": "..."}
    # Và trả về {"output": "..."}
    agent_executor_chain = (
        RunnablePassthrough.assign(
           # AgentExecutor cần input là "input" và "chat_history"
           # Chúng ta sẽ lấy chat_history từ input
           input=lambda x: x["user_input"],
           chat_history=lambda x: x.get("chat_history", []) # Lấy history, nếu không có thì dùng mảng rỗng
        )
        | agent_executor_obj # Dùng biến đã đổi tên
    )
    
    print("--- [Agent Executor] Đã khởi tạo Luồng 3 (Thực thi Tool) ---")
    return agent_executor_chain

# Khởi tạo agent executor ngay khi load module
agent_executor = create_agent_executor()