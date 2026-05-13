from langchain_chroma import Chroma

from config import CHROMA_DIR, EMBEDDING_MODEL
from rag.document_loader import load_and_chunk_documents


def get_embeddings():
    """
    Creates the embedding model.
    Embeddings convert text into vectors so similar meanings can be searched.
    """
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )


def build_vector_store():
    """
    Builds Chroma vector database from policy documents.
    """

    documents = load_and_chunk_documents()

    if not documents:
        raise ValueError("No documents found in data folder.")

    embeddings = get_embeddings()

    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )

    return vector_store


def load_vector_store():
    """
    Loads existing Chroma vector database.
    """

    embeddings = get_embeddings()

    vector_store = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )

    return vector_store


if __name__ == "__main__":
    store = build_vector_store()
    print("Vector store created successfully.")