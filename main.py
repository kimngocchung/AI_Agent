# File: main.py (Phiên bản A+ hoàn chỉnh, hiển thị kết quả RAG)

from core.router import create_router
from langchain_core.messages import AIMessage

# Import các thành phần cần thiết từ thư viện rich
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.text import Text
from rich.padding import Padding

# --- KHỞI TẠO CÁC ĐỐI TƯỢNG GIAO DIỆN ---
console = Console()
agent_chain = create_router()

# --- HÀM CHÍNH ĐỂ CHẠY AGENT ---
def run_agent(user_input: str):
    with console.status("[bold cyan]Cyber-Mentor đang phân tích...", spinner="dots8"):
        response = agent_chain.invoke({"user_input": user_input})

    console.print()

    if isinstance(response, dict) and 'final_report' in response:
        console.print(Panel("[bold yellow]🔎 ĐANG QUAN SÁT CHUỖI TƯ DUY CỦA AI 🔎[/bold yellow]", border_style="yellow", expand=False))

        # Hiển thị kết quả của từng bước trung gian
        steps = {
            "BƯỚC 1: KẾT QUẢ THU THẬP THÔNG TIN": response.get("recon_results"),
            "BƯỚC 2: KẾT QUẢ PHÂN TÍCH LỖ HỔNG": response.get("analysis_results"),
            "BƯỚC 3: KẾT QUẢ LÊN KẾ HOẠCH KHAI THÁC": response.get("exploitation_results"),
            "BƯỚC 4: KẾT QUẢ HẬU KHAI THÁC & BÁO CÁO": response.get("post_exploitation_results"),
            # <<< THÊM BƯỚC MỚI Ở ĐÂY >>>
            "BƯỚC 5: PAYLOAD & HƯỚNG DẪN CHI TIẾT (TỪ RAG)": response.get("actionable_intelligence"),
        }

        for title, content in steps.items():
            if content and isinstance(content, AIMessage):
                panel = Panel(
                    Padding(Markdown(content.content), (1, 2)),
                    title=f"[bold cyan]{title}[/bold cyan]",
                    border_style="cyan",
                    title_align="left"
                )
                console.print(panel)

        # Cuối cùng, hiển thị báo cáo tổng hợp
        final_report_content = response['final_report'].content if isinstance(response['final_report'], AIMessage) else str(response['final_report'])
        final_panel = Panel(
            Markdown(final_report_content),
            title="[bold green]✅ BÁO CÁO TỔNG HỢP CUỐI CÙNG ✅[/bold green]",
            border_style="green",
            title_align="left"
        )
        console.print(final_panel)

    elif isinstance(response, AIMessage):
        response_panel = Panel(
            Markdown(response.content),
            title="[bold green]🤖 Phản hồi từ Cyber-Mentor[/bold green]",
            border_style="green",
            title_align="left"
        )
        console.print(response_panel)
    
    else:
        console.print(str(response))

    console.print()


# --- VÒNG LẶP TƯƠNG TÁC VỚI NGƯỜI DÙNG (Không thay đổi) ---
if __name__ == "__main__":
    welcome_panel = Panel(
        Text("Chào mừng đến với AI Pentesting Agent.\nHãy bắt đầu bằng cách nhập yêu cầu của bạn bên dưới.\nNhập 'exit', 'quit' hoặc 'thoat' để kết thúc.", justify="center"),
        title="[bold blue]🚀 Cyber-Mentor AI 🚀[/bold blue]",
        border_style="blue"
    )
    console.print(welcome_panel)

    while True:
        try:
            user_input = Prompt.ask("[bold yellow]👨‍💻 Bạn[/bold yellow]")
            if user_input.lower() in ['exit', 'quit', 'thoat']:
                console.print(Panel("[bold cyan]👋 Tạm biệt! Hẹn gặp lại.[/bold cyan]", border_style="cyan"))
                break
            if user_input.strip():
                run_agent(user_input)
            else:
                console.print(Panel("[bold red]Lỗi: Vui lòng nhập yêu cầu của bạn.[/bold red]", border_style="red"))
        except KeyboardInterrupt:
            console.print(Panel("\n[bold cyan]👋 Tạm biệt! Đã dừng chương trình.[/bold cyan]", border_style="cyan"))
            break
