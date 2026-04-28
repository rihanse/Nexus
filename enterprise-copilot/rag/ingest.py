"""
Document ingestion pipeline using FAISS (no C++ build tools required on Windows).
Supports both .txt and .pdf files with RBAC metadata.
"""
import json
import os
import pickle
from pathlib import Path

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

FAISS_INDEX_DIR: str = os.getenv("FAISS_INDEX_DIR", "./faiss_index")
DOCS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")

DOC_METADATA = {
    "hr_policy": {
        "department": "HR",
        "access_roles": ["employee", "manager", "hr_team", "admin"],
    },
    "it_sop": {
        "department": "IT",
        "access_roles": ["employee", "manager", "it_team", "admin"],
    },
    "finance_rules": {
        "department": "Finance",
        "access_roles": ["employee", "manager", "finance_team", "admin"],
    },
}


def _resolve_metadata(filename: str) -> dict:
    """Resolve RBAC metadata from the filename stem."""
    stem = Path(filename).stem.lower()
    for key, meta in DOC_METADATA.items():
        if key in stem:
            return meta
    return {
        "department": "General",
        "access_roles": ["employee", "manager", "hr_team", "it_team", "finance_team", "admin"],
    }


def _load_documents(docs_dir: str) -> list:
    """Load all .txt and optionally .pdf files from docs_dir."""
    all_docs = []
    path = Path(docs_dir)
    if not path.exists():
        print(f"⚠️  Docs directory not found: {docs_dir}")
        return all_docs

    for fp in path.iterdir():
        if fp.suffix.lower() == ".txt":
            try:
                docs = TextLoader(str(fp), encoding="utf-8").load()
                all_docs.extend(docs)
                print(f"  📄 Loaded TXT: {fp.name}")
            except Exception as e:
                print(f"  ❌ {fp.name}: {e}")
        elif fp.suffix.lower() == ".pdf":
            try:
                from langchain_community.document_loaders import PyPDFLoader
                docs = PyPDFLoader(str(fp)).load()
                all_docs.extend(docs)
                print(f"  📄 Loaded PDF: {fp.name} ({len(docs)} pages)")
            except Exception as e:
                print(f"  ❌ {fp.name}: {e}")

    return all_docs


def ingest_documents(docs_dir: str = DOCS_DIR, index_dir: str = FAISS_INDEX_DIR) -> None:
    """
    Full ingestion pipeline: load → split → tag RBAC metadata → embed → persist FAISS index.

    Args:
        docs_dir: Directory containing .txt and .pdf policy documents.
        index_dir: Directory to save the FAISS index.
    """
    print(f"\n🔄 Starting ingestion from: {docs_dir}")
    raw_docs = _load_documents(docs_dir)
    if not raw_docs:
        print("❌ No documents found. Skipping ingestion.")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(raw_docs)
    print(f"  ✂️  {len(chunks)} chunks created.")

    # Tag each chunk with RBAC metadata
    for chunk in chunks:
        source = chunk.metadata.get("source", "")
        filename = Path(source).name
        meta = _resolve_metadata(filename)
        chunk.metadata["source"] = filename
        chunk.metadata["department"] = meta["department"]
        chunk.metadata["access_roles"] = json.dumps(meta["access_roles"])

    print("  🤖 Loading embedding model (first run downloads ~90MB)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Build FAISS index
    vectorstore = FAISS.from_documents(chunks, embeddings)

    # Persist to disk
    os.makedirs(index_dir, exist_ok=True)
    vectorstore.save_local(index_dir)

    # Also save raw chunks for metadata filtering
    meta_path = os.path.join(index_dir, "chunk_metadata.pkl")
    with open(meta_path, "wb") as f:
        pickle.dump([c.metadata for c in chunks], f)

    print(f"✅ Ingestion complete! {len(chunks)} chunks indexed and saved to '{index_dir}'.\n")


if __name__ == "__main__":
    ingest_documents()
