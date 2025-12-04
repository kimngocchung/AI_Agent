"""
AI Content Generator
Generate summaries and questions using Gemini
"""

import os
from google import generativeai as genai
from typing import List, Tuple

def generate_document_summary(content: str, filename: str) -> Tuple[str, List[str]]:
    """
    Generate summary and key points for a document
    
    Args:
        content: Document content
        filename: Document name
        
    Returns:
        (summary: str, key_points: List[str])
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Summary unavailable (no API key)", []
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Truncate content if too long (max 30,000 chars)
        truncated_content = content[:30000] if len(content) > 30000 else content
        
        prompt = f"""Phân tích tài liệu có tiêu đề "{filename}" và cung cấp:

1. Một bản tóm tắt ngắn gọn 2-3 câu bằng Tiếng Việt.
2. 3-5 điểm chính hoặc chủ đề bao gồm trong tài liệu (bằng Tiếng Việt).

Nội dung tài liệu:
{truncated_content}

Định dạng phản hồi của bạn như sau:
TÓM TẮT: [nội dung tóm tắt của bạn]
ĐIỂM CHÍNH:
- [điểm 1]
- [điểm 2]
- [điểm 3]
"""
        
        response = model.generate_content(prompt)
        text = response.text
        
        # Parse response
        summary = ""
        key_points = []
        
        lines = text.split('\n')
        in_key_points = False
        
        for line in lines:
            if line.startswith("TÓM TẮT:") or line.startswith("SUMMARY:"):
                summary = line.replace("TÓM TẮT:", "").replace("SUMMARY:", "").strip()
            elif line.startswith("ĐIỂM CHÍNH:") or line.startswith("KEY_POINTS:"):
                in_key_points = True
            elif in_key_points and line.strip().startswith("-"):
                key_points.append(line.strip()[1:].strip())
        
        # Fallback if parsing failed
        if not summary:
            summary = text[:500] + "..." if len(text) > 500 else text
        
        return summary, key_points
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return f"Lỗi: {str(e)}", []

def generate_suggested_questions(content: str, filename: str) -> List[str]:
    """
    Generate 3-5 insightful questions about the document
    
    Args:
        content: Document content
        filename: Document name
        
    Returns:
        List of suggested questions
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return []
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Truncate content
        truncated_content = content[:30000] if len(content) > 30000 else content
        
        prompt = f"""Dựa trên tài liệu có tiêu đề "{filename}", hãy tạo ra 5 câu hỏi sâu sắc bằng Tiếng Việt giúp người đọc hiểu rõ hơn về các khái niệm chính.

Nội dung tài liệu:
{truncated_content}

Chỉ trả về CÁC CÂU HỎI, mỗi câu một dòng, không đánh số hay định dạng thêm.
Các câu hỏi phải cụ thể, thực tế và liên quan đến chủ đề chính của tài liệu.
"""
        
        response = model.generate_content(prompt)
        text = response.text
        
        # Parse questions
        questions = []
        for line in text.split('\n'):
            line = line.strip()
            # Remove numbering like "1.", "Q1:", etc.
            line = line.lstrip('0123456789.- ') .strip()
            line = line.replace('Q:', '').replace('?', '').strip()
            if line and len(line) > 10:  # Minimum length check
                questions.append(line + "?")
        
        return questions[:5]  # Return max 5
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        return []
