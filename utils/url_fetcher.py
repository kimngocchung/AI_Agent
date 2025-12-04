"""
URL Content Fetcher
Fetch and process content from URLs
"""

import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document

def fetch_url_content(url: str) -> tuple[bool, str, str]:
    """
    Fetch content from URL
    
    Args:
        url: URL to fetch
        
    Returns:
        (success: bool, content: str, error: str)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style tags
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return True, text, ""
        
    except requests.exceptions.RequestException as e:
        return False, "", f"Error fetching URL: {str(e)}"
    except Exception as e:
        return False, "", f"Error processing content: {str(e)}"

def url_to_document(url: str) -> tuple[bool, Document, str]:
    """
    Convert URL to Document
    
    Returns:
        (success: bool, document: Document, error: str)
    """
    success, content, error = fetch_url_content(url)
    
    if not success:
        return False, None, error
    
    doc = Document(
        page_content=content,
        metadata={'source': url, 'type': 'url'}
    )
    
    return True, doc, ""
