"""
Source Manager
Manage uploaded sources (list, count, delete)
"""

import json
import os
from typing import List, Dict
from datetime import datetime

SOURCES_FILE = "uploaded_sources.json"

def load_sources() -> List[Dict]:
    """Load sources from JSON file"""
    if os.path.exists(SOURCES_FILE):
        try:
            with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_sources(sources: List[Dict]):
    """Save sources to JSON file"""
    with open(SOURCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)

def add_source(name: str, type: str, size: int = 0, summary: str = "", suggested_questions: List[str] = None) -> bool:
    """
    Add a new source to the list
    
    Args:
        name: Source name (filename or URL)
        type: Source type (pdf, txt, url, text, etc.)
        size: File size in bytes
        summary: Document summary
        suggested_questions: List of suggested questions
        
    Returns:
        True if added successfully
    """
    try:
        sources = load_sources()
        
        source = {
            "name": name,
            "type": type,
            "size": size,
            "uploaded_at": datetime.now().isoformat(),
            "chunks": 0,  # Will be updated after processing
            "summary": summary,
            "suggested_questions": suggested_questions or []
        }
        
        sources.append(source)
        save_sources(sources)
        return True
    except Exception as e:
        print(f"Error adding source: {e}")
        return False

def get_source_count() -> int:
    """Get total number of sources"""
    return len(load_sources())

def update_source_chunks(name: str, chunk_count: int):
    """Update chunk count for a source"""
    sources = load_sources()
    for source in sources:
        if source["name"] == name:
            source["chunks"] = chunk_count
            break
    save_sources(sources)

def delete_source(name: str) -> bool:
    """Delete a source from the list"""
    try:
        sources = load_sources()
        sources = [s for s in sources if s["name"] != name]
        save_sources(sources)
        return True
    except:
        return False

def get_sources_by_type(source_type: str = None) -> List[Dict]:
    """Get sources filtered by type"""
    sources = load_sources()
    if source_type:
        return [s for s in sources if s["type"] == source_type]
    return sources

def update_source_summary(name: str, summary: str, suggested_questions: List[str]):
    """Update summary and questions for a source"""
    sources = load_sources()
    for source in sources:
        if source["name"] == name:
            source["summary"] = summary
            source["suggested_questions"] = suggested_questions
            break
    save_sources(sources)

def get_source_by_name(name: str) -> Dict:
    """Get a source by name"""
    sources = load_sources()
    for source in sources:
        if source["name"] == name:
            return source
    return None

def update_source_summary(name: str, summary: str, suggested_questions: List[str]):
    """Update summary and questions for a source"""
    sources = load_sources()
    for source in sources:
        if source["name"] == name:
            source["summary"] = summary
            source["suggested_questions"] = suggested_questions
            break
    save_sources(sources)

def get_source_by_name(name: str) -> Dict:
    """Get a source by name"""
    sources = load_sources()
    for source in sources:
        if source["name"] == name:
            return source
    return None
