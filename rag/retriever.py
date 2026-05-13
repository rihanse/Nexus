from langchain_core.prompts import ChatPromptTemplate

from config import (
    MODEL_PROVIDER,
    LLM_MODEL,
    GEMINI_API_KEY,
    GROQ_API_KEY,
    OPENAI_API_KEY
)

from rag.vector_store import load_vector_store


def get_llm():
    """
    Returns an LLM based on MODEL_PROVIDER.
    If no API key is configured, returns None and fallback answer will be used.
    """

    provider = MODEL_PROVIDER.lower().strip()

    if provider == "gemini" and GEMINI_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=0
        )

    if provider == "groq" and GROQ_API_KEY:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=LLM_MODEL,
            groq_api_key=GROQ_API_KEY,
            temperature=0
        )

    if provider == "openai" and OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=LLM_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0
        )

    return None


def role_allowed_for_document(role: str, document_metadata: dict) -> bool:
    """
    Simple RBAC document filter.
    Current policy documents are marked access='all',
    so all roles can read them.

    Later, if we add restricted documents, this function will block access.
    """

    role = role.lower().strip()
    access = document_metadata.get("access", "all")
    department = document_metadata.get("department", "general")

    if access == "all":
        return True

    if role == "admin":
        return True

    if department == "hr" and role in ["hr", "manager"]:
        return True

    if department == "it" and role in ["it"]:
        return True

    if department == "finance" and role in ["finance"]:
        return True

    return False


def format_sources(documents) -> str:
    """
    Formats unique source file names.
    """

    sources = []

    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        if source not in sources:
            sources.append(source)

    return ", ".join(sources)


def fallback_answer(question: str, documents) -> str:
    """
    Used when no LLM API key is configured.
    It returns the most relevant retrieved policy text.
    """

    context_lines = []

    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        content = doc.page_content.strip()
        context_lines.append(f"From {source}:\n{content}")

    sources = format_sources(documents)

    return (
        f"Based on the internal policy documents, here is the relevant information:\n\n"
        f"{chr(10).join(context_lines)}\n\n"
        f"Source: {sources}"
    )


def answer_policy_question(
    question: str,
    role: str = "employee",
    k: int = 3
) -> dict:
    """
    Main RAG function.
    It retrieves top-k relevant chunks and generates a source-aware answer.
    """

    vector_store = load_vector_store()

    retrieved_docs = vector_store.similarity_search(
        query=question,
        k=k
    )

    allowed_docs = [
        doc for doc in retrieved_docs
        if role_allowed_for_document(role, doc.metadata)
    ]

    if not allowed_docs:
        return {
            "success": False,
            "answer": "You do not have access to the relevant policy documents.",
            "sources": ""
        }

    llm = get_llm()

    if llm is None:
        return {
            "success": True,
            "answer": fallback_answer(question, allowed_docs),
            "sources": format_sources(allowed_docs)
        }

    context = "\n\n".join(
        [
            f"Source: {doc.metadata.get('source')}\n{doc.page_content}"
            for doc in allowed_docs
        ]
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
You are Workplace Buddy, an internal enterprise AI copilot.

Answer the user's question using only the provided internal policy context.
Be clear, concise, and professional.
If the answer is not available in the context, say that the policy document does not contain that information.
Always include the source file names at the end.
"""
            ),
            (
                "human",
                """
Question:
{question}

Internal Policy Context:
{context}

Source files:
{sources}
"""
            )
        ]
    )

    chain = prompt | llm

    try:
        response = chain.invoke(
            {
                "question": question,
                "context": context,
                "sources": format_sources(allowed_docs)
            }
        )

        return {
            "success": True,
            "answer": response.content,
            "sources": format_sources(allowed_docs)
        }
    except Exception as e:
        return {
            "success": False,
            "answer": "I am currently unable to process this request due to an AI model error. Please try again later.",
            "sources": format_sources(allowed_docs)
        }


if __name__ == "__main__":
    result = answer_policy_question(
        question="How many casual leaves are allowed?",
        role="employee"
    )

    print(result["answer"])