# File: core/router.py (Phiên bản tinh gọn cho kiến trúc A+)

# Bây giờ, file này chỉ có nhiệm vụ import và cung cấp chain chính.
# Toàn bộ logic phân loại và rẽ nhánh đã được loại bỏ vì không còn cần thiết.
from .chains.full_plan_chain import full_plan_chain

def create_router():
    """
    Hàm này giờ đây chỉ trả về chain xử lý chính và duy nhất của chúng ta.
    Nó không còn thực hiện việc định tuyến (routing) nữa.
    """
    return full_plan_chain
