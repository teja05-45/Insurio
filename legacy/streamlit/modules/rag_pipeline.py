"""
RAG (Retrieval Augmented Generation) pipeline for PolicyPilot AI.
Handles document parsing, chunking, embedding, and retrieval.
"""

import re
import math
from typing import List, Tuple
import streamlit as st
from modules.sanitize import sanitize_rag_context

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


# ─── Document Parsing ────────────────────────────────────────────────────────

def extract_text_from_pdf(uploaded_file) -> dict:
    """
    Extract text from uploaded PDF file.
    
    Returns:
        dict with 'text', 'pages', and 'error' keys
    """
    if not PYMUPDF_AVAILABLE:
        return {
            "text": None,
            "pages": 0,
            "error": "PyMuPDF not installed. Run: pip install pymupdf"
        }
    
    try:
        file_bytes = uploaded_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        full_text = []
        page_count = len(doc)  # capture BEFORE closing
        for page_num, page in enumerate(doc, 1):
            text = page.get_text("text")
            if text.strip():
                full_text.append(f"\n[Page {page_num}]\n{text}")

        doc.close()
        combined = "\n".join(full_text)

        if not combined.strip():
            return {"text": None, "pages": 0, "error": "Could not extract text. The PDF may be scanned/image-based."}

        return {"text": combined, "pages": page_count, "error": None}
    
    except Exception as e:
        return {"text": None, "pages": 0, "error": f"PDF parsing error: {str(e)}"}


# ─── Text Chunking ────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """
    Split text into overlapping chunks for embedding.
    
    Args:
        text: Full document text
        chunk_size: Target characters per chunk
        overlap: Overlap between consecutive chunks
    
    Returns:
        List of text chunks
    """
    # Clean text
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    # Try to split on paragraph boundaries first
    paragraphs = re.split(r'\n\n+', text)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If adding this paragraph exceeds chunk size, save current and start new
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Keep overlap from end of current chunk
            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
            current_chunk = overlap_text + "\n\n" + para
        else:
            current_chunk += "\n\n" + para if current_chunk else para
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Handle very long paragraphs by splitting on sentences
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > chunk_size * 1.5:
            sentences = re.split(r'(?<=[.!?])\s+', chunk)
            sub_chunk = ""
            for sent in sentences:
                if len(sub_chunk) + len(sent) > chunk_size and sub_chunk:
                    final_chunks.append(sub_chunk.strip())
                    sub_chunk = sub_chunk[-overlap:] + " " + sent
                else:
                    sub_chunk += " " + sent if sub_chunk else sent
            if sub_chunk.strip():
                final_chunks.append(sub_chunk.strip())
        else:
            final_chunks.append(chunk)
    
    return [c for c in final_chunks if len(c) > 50]


# ─── Embedding & Vector Store ─────────────────────────────────────────────────

class SimpleVectorStore:
    """
    Lightweight in-memory vector store using cosine similarity.
    Falls back to keyword search if embeddings unavailable.
    """
    
    def __init__(self):
        self.chunks = []
        self.embeddings = []
        self.model = None
        self.use_embeddings = False
    
    def build(self, chunks: List[str]) -> dict:
        """Build vector store from text chunks."""
        self.chunks = chunks
        
        if EMBEDDINGS_AVAILABLE:
            try:
                with st.spinner("Generating embeddings..."):
                    self.model = SentenceTransformer('all-MiniLM-L6-v2')
                    import numpy as np
                    self.embeddings = self.model.encode(chunks, show_progress_bar=False)
                    self.use_embeddings = True
                return {"success": True, "method": "embeddings", "chunks": len(chunks)}
            except Exception as e:
                self.use_embeddings = False
                return {"success": True, "method": "keyword", "chunks": len(chunks), "warning": str(e)}
        else:
            self.use_embeddings = False
            return {"success": True, "method": "keyword", "chunks": len(chunks)}
    
    def search(self, query: str, top_k: int = 5) -> List[str]:
        """Retrieve most relevant chunks for a query."""
        if not self.chunks:
            return []
        
        if self.use_embeddings and self.model is not None:
            return self._embedding_search(query, top_k)
        else:
            return self._keyword_search(query, top_k)
    
    def _embedding_search(self, query: str, top_k: int) -> List[str]:
        """Cosine similarity search using embeddings."""
        try:
            import numpy as np
            query_embedding = self.model.encode([query])[0]
            
            # Cosine similarity
            norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
            norms = np.where(norms == 0, 1e-10, norms)
            similarities = np.dot(self.embeddings, query_embedding) / norms
            
            top_indices = np.argsort(similarities)[::-1][:top_k]
            return [self.chunks[i] for i in top_indices]
        except Exception:
            return self._keyword_search(query, top_k)
    
    def _keyword_search(self, query: str, top_k: int) -> List[str]:
        """TF-IDF inspired keyword search fallback."""
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'is', 'it', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 'but', 'what', 'how', 'does', 'do', 'my', 'i', 'me', 'are', 'was', 'be'}
        query_words -= stop_words
        
        scores = []
        for i, chunk in enumerate(self.chunks):
            chunk_lower = chunk.lower()
            chunk_words = set(re.findall(r'\b\w+\b', chunk_lower))
            
            # Score based on keyword overlap + exact phrase matches
            overlap = len(query_words & chunk_words)
            phrase_bonus = sum(2 for word in query_words if word in chunk_lower)
            score = overlap + phrase_bonus
            scores.append((score, i))
        
        scores.sort(reverse=True)
        top_indices = [i for _, i in scores[:top_k] if scores[0][0] > 0]
        
        if not top_indices:
            # Return first chunks as fallback
            return self.chunks[:min(top_k, len(self.chunks))]
        
        return [self.chunks[i] for i in top_indices]


# ─── Public Interface ─────────────────────────────────────────────────────────

def process_document(uploaded_file) -> dict:
    """
    Full pipeline: parse PDF → chunk → build vector store.
    
    Returns:
        dict with 'vector_store', 'text', 'chunks', 'pages', 'error'
    """
    # Extract text
    result = extract_text_from_pdf(uploaded_file)
    if result["error"]:
        return {"error": result["error"]}
    
    text = result["text"]
    pages = result["pages"]
    
    # Chunk text
    chunks = chunk_text(text)
    if not chunks:
        return {"error": "Could not extract meaningful text from the document."}

    # Strip any HTML that may have survived PDF extraction (web-sourced PDFs)
    chunks = [sanitize_rag_context(c) for c in chunks]
    chunks = [c for c in chunks if len(c) > 50]  # re-filter after stripping
    if not chunks:
        return {"error": "Document contained no extractable text after cleaning."}
    
    # Build vector store
    store = SimpleVectorStore()
    build_result = store.build(chunks)
    
    return {
        "vector_store": store,
        "text": text,
        "chunks": chunks,
        "pages": pages,
        "chunk_count": len(chunks),
        "retrieval_method": build_result.get("method", "keyword"),
        "error": None
    }


def retrieve_context(vector_store: SimpleVectorStore, question: str, top_k: int = 4) -> str:
    """
    Retrieve relevant context chunks for a question.
    
    Returns:
        Formatted context string
    """
    if vector_store is None:
        return ""
    
    chunks = vector_store.search(question, top_k=top_k)
    raw_context = "\n\n---\n\n".join(chunks)
    return sanitize_rag_context(raw_context)