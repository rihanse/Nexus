from pathlib import Path
from langchain_core.documents import Document

DATA_DIR = Path("data")


def detect_department(filename: str) -> str:
    """
    Detects which department the document belongs to based on file name.
    This metadata will later help with RBAC-based retrieval.
    """

    filename = filename.lower()

    if "hr" in filename:
        return "hr"

    if "it" in filename:
        return "it"

    if "finance" in filename:
        return "finance"

    return "general"


def load_text_documents() -> list[Document]:
    """
    Loads all .txt files from the data folder and converts them into LangChain Documents.
    """

    documents = []

    for file_path in DATA_DIR.glob("*.txt"):
        text = file_path.read_text(encoding="utf-8")

        department = detect_department(file_path.name)

        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": file_path.name,
                    "department": department,
                    "access": "all"
                }
            )
        )

    return documents


def chunk_documents(documents: list[Document]) -> list[Document]:
    """
    Splits large documents into smaller chunks for better retrieval.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80
    )

    chunks = splitter.split_documents(documents)

    return chunks


def load_and_chunk_documents() -> list[Document]:
    """
    Full document loading pipeline:
    Load documents -> Split into chunks.
    """

    documents = load_text_documents()
    chunks = chunk_documents(documents)

    return chunks


if __name__ == "__main__":
    chunks = load_and_chunk_documents()

    print(f"Loaded and chunked {len(chunks)} document chunks.")

    for chunk in chunks:
        print("-" * 50)
        print("Source:", chunk.metadata["source"])
        print("Department:", chunk.metadata["department"])
        print(chunk.page_content[:200])