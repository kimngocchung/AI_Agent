"""
Document Processor
Process uploaded documents and add to FAISS index
"""

import os
from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
import tempfile

def process_pdf(file_bytes, filename: str) -> List[Document]:
    """Extract text from PDF file"""
    try:
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        
        loader = PyPDFLoader(tmp_path)
        docs = loader.load()
        
        # Clean up
        os.unlink(tmp_path)
        
        # Add metadata
        for doc in docs:
            doc.metadata['source'] = filename
            
        return docs
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return []

def process_txt(file_bytes, filename: str) -> List[Document]:
    """Read TXT file"""
    try:
        text = file_bytes.decode('utf-8')
        doc = Document(page_content=text, metadata={'source': filename})
        return [doc]
    except Exception as e:
        print(f"Error processing TXT: {e}")
        return []

def process_docx(file_bytes, filename: str) -> List[Document]:
    """Extract text from DOCX file"""
    try:
        from docx import Document as DocxDocument
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        
        doc = DocxDocument(tmp_path)
        text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
        
        # Clean up
        os.unlink(tmp_path)
        
        return [Document(page_content=text, metadata={'source': filename})]
    except Exception as e:
        print(f"Error processing DOCX: {e}")
        return []

def process_md(file_bytes, filename: str) -> List[Document]:
    """Read Markdown file"""
    try:
        text = file_bytes.decode('utf-8')
        doc = Document(page_content=text, metadata={'source': filename})
        return [doc]
    except Exception as e:
        print(f"Error processing MD: {e}")
        return []

def chunk_documents(docs: List[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Document]:
    """Split documents into chunks"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    return text_splitter.split_documents(docs)

def add_to_faiss(docs: List[Document], faiss_path: str) -> tuple[bool, str]:
    """
    Add documents to FAISS index
    
    Args:
        docs: List of documents to add
        faiss_path: Path to FAISS index directory
        
    Returns:
        (success: bool, message: str)
    """
    try:
        # Initialize embeddings
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        # Check if index exists
        if os.path.exists(faiss_path):
            # Load existing index
            vectorstore = FAISS.load_local(
                faiss_path,
                embeddings,
                allow_dangerous_deserialization=True
            )
            
            # Add new documents
            vectorstore.add_documents(docs)
            
            # Save updated index
            vectorstore.save_local(faiss_path)
            
            return True, f"✅ Added {len(docs)} chunks to existing FAISS index"
        else:
            # Create new index
            vectorstore = FAISS.from_documents(docs, embeddings)
            vectorstore.save_local(faiss_path)
            
            return True, f"✅ Created new FAISS index with {len(docs)} chunks"
            
    except Exception as e:
        return False, f"❌ Error adding to FAISS: {str(e)}"

def get_faiss_stats(faiss_path: str) -> dict:
    """
    Get statistics about FAISS index
    
    Returns:
        dict with stats (exists, doc_count, etc.)
    """
    try:
        if not os.path.exists(faiss_path):
            return {"exists": False, "doc_count": 0}
        
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        
        vectorstore = FAISS.load_local(
            faiss_path,
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        # Get document count
        doc_count = vectorstore.index.ntotal
        
        return {
            "exists": True,
            "doc_count": doc_count
        }
    except Exception as e:
        print(f"Error getting FAISS stats: {e}")
        return {"exists": False, "doc_count": 0, "error": str(e)}
