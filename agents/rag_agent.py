from rag.retriever import answer_policy_question


def rag_agent_node(question: str, role: str = "employee") -> dict:
    """
    RAG Agent handles policy-related questions.
    """

    result = answer_policy_question(
        question=question,
        role=role,
        k=3
    )

    return {
        "success": result["success"],
        "message": result["answer"],
        "agent": "rag_agent",
        "sources": result.get("sources", "")
    }