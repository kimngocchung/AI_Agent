# File: core/chains/tool_agent.py

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from core.tools import all_tools

# 1. Khởi tạo LLM
llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.2)

# 2. Lấy danh sách các công cụ từ __init__.py
tools = all_tools

# 3. Tạo Prompt Template
# Đây là "bộ não" của Agent, hướng dẫn nó cách suy nghĩ và hành động.
prompt_template = """
Bạn là một chuyên gia pentest tự động, được gọi là "HexStrike Agent".
Nhiệm vụ của bạn là sử dụng các công cụ có sẵn để thực hiện các yêu cầu của người dùng một cách an toàn và hiệu quả.

BẠN CÓ QUYỀN TRUY CẬP VÀO CÁC CÔNG CỤ SAU:

{tools}

QUY TRÌNH SUY NGHĨ VÀ HÀNH ĐỘNG:
1.  **Question**: Phân tích yêu cầu ban đầu của người dùng.
2.  **Thought**: Suy nghĩ từng bước một. Quyết định xem có cần sử dụng công cụ hay không. Nếu có, chọn công cụ PHÙ HỢP NHẤT từ danh sách.
3.  **Action**: Nếu quyết định dùng công cụ, hãy viết action dưới dạng một JSON block:
    ```json
    {{
      "action": "TÊN_CÔNG_CỤ",
      "action_input": {{
        "tham_so_1": "giá_trị_1",
        "tham_so_2": "giá_trị_2"
      }}
    }}
    ```
4.  **Observation**: Quan sát kết quả trả về từ công cụ.
5.  **Thought**: Dựa vào kết quả (Observation), quyết định bước tiếp theo. Có thể là sử dụng một công cụ khác, hoặc kết hợp các kết quả lại.
6.  ... (Lặp lại Thought/Action/Observation cho đến khi có đủ thông tin) ...
7.  **Thought**: Khi đã có đủ thông tin để trả lời yêu cầu ban đầu, hãy dừng lại.
8.  **Final Answer**: Đưa ra câu trả lời cuối cùng cho người dùng, tổng hợp tất cả các phát hiện của bạn một cách rõ ràng, mạch lạc.

BẮT ĐẦU!

Question: {input}
Thought: {agent_scratchpad}
"""

prompt = PromptTemplate.from_template(prompt_template)

# 4. Tạo Agent
# Agent là bộ điều phối, kết hợp LLM, tools và prompt
agent = create_react_agent(llm, tools, prompt)

# 5. Tạo Agent Executor
# AgentExecutor chịu trách nhiệm thực thi các vòng lặp Thought -> Action -> Observation
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True, # In ra các bước suy nghĩ của Agent
    handle_parsing_errors=True, # Xử lý lỗi nếu Agent trả về định dạng không đúng
    max_iterations=10, # Giới hạn số vòng lặp để tránh lặp vô hạn
)

print("--- [Tool Agent] Agent thực thi công cụ đã được khởi tạo --- ")
