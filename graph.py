import time
from typing import TypedDict, Optional, List, Dict

from langgraph.graph import StateGraph, START, END

from agents.router_agent import detect_intent
from agents.hr_agent import handle_hr_agent
from agents.it_agent import handle_it_agent
from agents.finance_agent import handle_finance_agent
from agents.rag_agent import rag_agent_node
from agents.approval_agent import handle_approval_agent

from middleware.rbac import validate_intent_access, get_user_role

from tools.memory_tools import save_memory
from tools.log_tools import save_log


class AgentState(TypedDict, total=False):
    user_input: str
    emp_id: str
    name: str
    role: str
    department: str
    chat_history: List[Dict[str, str]]
    request_id: Optional[int]
    ticket_id: Optional[int]
    action: Optional[str]
    target_type: Optional[str]

    intent: Optional[str]
    agent: Optional[str]
    confidence: Optional[float]
    reason: Optional[str]

    response: Optional[str]
    tool_used: Optional[str]
    status: Optional[str]

    start_time: Optional[float]
    response_time: Optional[float]


from tools.chat_history_tools import answer_chat_history_question

def detect_intent_node(state: AgentState) -> AgentState:
    """
    LangGraph node 1:
    Detects the user intent and target agent.
    """
    history_answer = answer_chat_history_question(
        state.get("user_input", ""),
        state.get("chat_history", [])
    )

    if history_answer:
        return {
            "intent": "chat_history",
            "agent": "chat_history_agent",
            "tool_used": "chat_history",
            "response": history_answer,
            "status": "success"
        }

    router_result = detect_intent(state.get("user_input", ""), state.get("chat_history", []))

    return {
        "intent": router_result["intent"],
        "agent": router_result["agent"],
        "confidence": router_result["confidence"],
        "reason": router_result["reason"],
        "request_id": router_result.get("request_id"),
        "ticket_id": router_result.get("ticket_id"),
        "action": router_result.get("action"),
        "target_type": router_result.get("target_type")
    }


def validate_access_node(state: AgentState) -> AgentState:
    """
    LangGraph node 2:
    Validates RBAC before allowing the request to continue.
    """

    access_result = validate_intent_access(
        intent=state["intent"],
        role=state["role"]
    )

    if not access_result["allowed"]:
        return {
            "response": access_result["message"],
            "tool_used": "rbac_validator",
            "status": "denied"
        }

    return {
        "status": "access_allowed"
    }


def small_talk_node(state: AgentState) -> AgentState:
    """
    Handles greetings and casual small talk.
    """

    text = state["user_input"].lower().strip()

    if text in ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]:
        response = (
            "Hi, I am Workplace Buddy. I can help with HR policies, leave requests, "
            "IT tickets, asset requests, and reimbursements."
        )
    elif "thank" in text:
        response = "You're welcome. Happy to help."
    elif "bye" in text or "goodbye" in text:
        response = "Goodbye. Have a great day."
    else:
        response = "Hello. How can I help you today?"

    return {
        "response": response,
        "tool_used": "small_talk",
        "status": "success"
    }


def rag_node(state: AgentState) -> AgentState:
    """
    Handles policy questions using RAG.
    """

    result = rag_agent_node(
        question=state["user_input"],
        role=state["role"]
    )

    return {
        "response": result["message"],
        "tool_used": "rag_retriever",
        "status": "success" if result["success"] else "failed"
    }


def hr_node(state: AgentState) -> AgentState:
    """
    Handles HR workflow actions.
    """

    return handle_hr_agent(state)


def it_node(state: AgentState) -> AgentState:
    """
    Handles IT ticket and asset workflow actions.
    """

    return handle_it_agent(state)


def finance_node(state: AgentState) -> AgentState:
    """
    Handles finance workflow actions.
    """

    return handle_finance_agent(state)


def approval_node(state: AgentState) -> AgentState:
    """
    Handles pending approvals check across all domains.
    """
    return handle_approval_agent(state)


def unknown_node(state: AgentState) -> AgentState:
    """
    Handles unsupported or unclear queries.
    """

    return {
        "response": (
            "I could not clearly understand your request. "
            "You can ask about HR policies, leave, IT tickets, asset requests, or reimbursements."
        ),
        "tool_used": "unknown_handler",
        "status": "unknown"
    }


def chat_history_agent(state: AgentState) -> AgentState:
    """
    Pass-through node for chat history answers.
    """
    return state


def decide_next_node(state: AgentState) -> str:
    """
    Decides which node should run after RBAC validation.
    """

    if state.get("status") == "denied":
        return "finalize"

    agent = state.get("agent")

    if agent == "hr_agent":
        return "hr_agent"

    if agent == "it_agent":
        return "it_agent"

    if agent == "finance_agent":
        return "finance_agent"

    if agent == "rag_agent":
        return "rag_agent"

    if agent == "small_talk_agent":
        return "small_talk_agent"

    if agent == "approval_agent":
        return "approval_agent"

    if agent == "chat_history_agent":
        return "chat_history_agent"

    return "unknown_agent"


def finalize_node(state: AgentState) -> AgentState:
    """
    Final node:
    Saves memory and logs for observability.
    """

    response = state.get("response") or "No response generated."

    start_time = state.get("start_time") or time.time()
    response_time = round(time.time() - start_time, 3)

    emp_id = state.get("emp_id", "")
    user_input = state.get("user_input", "")

    try:
        save_memory(
            emp_id=emp_id,
            user_message=user_input,
            assistant_response=response
        )
    except Exception as error:
        print(f"Memory save failed: {error}")

    try:
        save_log(
            emp_id=emp_id,
            user_query=user_input,
            intent=state.get("intent", "unknown"),
            agent_used=state.get("agent", "unknown_agent"),
            tool_used=state.get("tool_used", "unknown_tool"),
            status=state.get("status", "unknown"),
            response_time=response_time
        )
    except Exception as error:
        print(f"Log save failed: {error}")

    return {
        "response": response,
        "response_time": response_time
    }


def build_workflow():
    """
    Builds and compiles the LangGraph workflow.
    """

    graph = StateGraph(AgentState)

    graph.add_node("detect_intent", detect_intent_node)
    graph.add_node("validate_access", validate_access_node)

    graph.add_node("small_talk_agent", small_talk_node)
    graph.add_node("rag_agent", rag_node)
    graph.add_node("hr_agent", hr_node)
    graph.add_node("it_agent", it_node)
    graph.add_node("finance_agent", finance_node)
    graph.add_node("approval_agent", approval_node)
    graph.add_node("chat_history_agent", chat_history_agent)
    graph.add_node("unknown_agent", unknown_node)

    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "detect_intent")
    graph.add_edge("detect_intent", "validate_access")

    graph.add_conditional_edges(
        "validate_access",
        decide_next_node,
        {
            "small_talk_agent": "small_talk_agent",
            "rag_agent": "rag_agent",
            "hr_agent": "hr_agent",
            "it_agent": "it_agent",
            "finance_agent": "finance_agent",
            "approval_agent": "approval_agent",
            "chat_history_agent": "chat_history_agent",
            "unknown_agent": "unknown_agent",
            "finalize": "finalize"
        }
    )

    graph.add_edge("small_talk_agent", "finalize")
    graph.add_edge("rag_agent", "finalize")
    graph.add_edge("hr_agent", "finalize")
    graph.add_edge("it_agent", "finalize")
    graph.add_edge("finance_agent", "finalize")
    graph.add_edge("approval_agent", "finalize")
    graph.add_edge("chat_history_agent", "finalize")
    graph.add_edge("unknown_agent", "finalize")

    graph.add_edge("finalize", END)

    return graph.compile()


workflow = build_workflow()


def run_workflow(user_input: str, emp_id: str, role: str | None = None, name: str | None = None, department: str | None = None, chat_history: list | None = None) -> dict:
    """
    Main function used by app.py later.
    It runs the complete Workplace Buddy workflow.
    """

    db_role = get_user_role(emp_id)

    final_role = db_role or role or "employee"

    initial_state: AgentState = {
        "user_input": user_input,
        "emp_id": emp_id,
        "name": name or "",
        "department": department or "",
        "role": final_role,
        "chat_history": chat_history or [],
        "start_time": time.time()
    }

    result = workflow.invoke(initial_state)

    return {
        "response": result.get("response", "No response generated."),
        "intent": result.get("intent"),
        "agent": result.get("agent"),
        "tool_used": result.get("tool_used"),
        "status": result.get("status"),
        "role": final_role,
        "response_time": result.get("response_time")
    }


if __name__ == "__main__":
    output = run_workflow(
        user_input="Hi",
        emp_id="EMP001"
    )

    print(output["response"])