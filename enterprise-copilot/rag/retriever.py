"""
RBAC-aware retriever using FAISS (no C++ build tools required on Windows).
"""
import json
import os
import pickle
from typing import Optional

from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

FAISS_INDEX_DIR: str = os.getenv("FAISS_INDEX_DIR", "./faiss_index")

_vectorstore: Optional[FAISS] = None
_embeddings = None


def _get_embeddings():
    """Lazily load the embedding model (downloaded once, cached)."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embeddings


def _get_vectorstore() -> Optional[FAISS]:
    """Lazily load the FAISS index from disk."""
    global _vectorstore
    if _vectorstore is None:
        if not os.path.exists(FAISS_INDEX_DIR):
            print(f"⚠️  FAISS index not found at '{FAISS_INDEX_DIR}'. Run ingest_documents() first.")
            return None
        try:
            _vectorstore = FAISS.load_local(
                FAISS_INDEX_DIR,
                _get_embeddings(),
                allow_dangerous_deserialization=True,
            )
        except Exception as e:
            print(f"⚠️  Could not load FAISS index: {e}")
            return None
    return _vectorstore


def retrieve_relevant_docs(
    query: str,
    user_role: str,
    department: Optional[str] = None,
    k: int = 5,
) -> list[dict]:
    """
    Retrieve top-k relevant document chunks, filtered by RBAC role and optional department.

    Args:
        query: User query string.
        user_role: Role of the requesting user (for RBAC filtering).
        department: Optional department filter (HR, IT, Finance, General).
        k: Number of chunks to return after filtering.

    Returns:
        List of dicts with content, source, department, score.
    """
    vs = _get_vectorstore()
    if vs is None:
        return []

    try:
        # Fetch more than k to allow for RBAC filtering
        results = vs.similarity_search_with_score(query, k=k * 5)
    except Exception as e:
        print(f"⚠️  FAISS search error: {e}")
        return []

    filtered = []
    for doc, score in results:
        # RBAC check
        try:
            access_roles = json.loads(doc.metadata.get("access_roles", "[]"))
        except Exception:
            access_roles = []

        if user_role not in access_roles:
            continue

        # Optional department filter
        doc_dept = doc.metadata.get("department", "")
        if department and doc_dept.lower() != department.lower():
            continue

        filtered.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "department": doc_dept,
            "score": float(score),
        })

        if len(filtered) >= k:
            break

    return filtered


def format_context(docs: list[dict]) -> str:
    """
    Format retrieved chunks into a numbered context string for LLM prompts.

    Args:
        docs: List of dicts from retrieve_relevant_docs.

    Returns:
        Formatted multi-line string.
    """
    if not docs:
        return "No relevant documents found."
    lines = ["RELEVANT POLICY CONTEXT:\n"]
    for i, doc in enumerate(docs, 1):
        lines.append(f"[{i}] Source: {doc['source']} (Dept: {doc['department']})")
        lines.append(doc["content"].strip())
        lines.append("")
    return "\n".join(lines)
