"""
Router Agent — main LangGraph supervisor that classifies intent and routes to domain agents.
Gemini-compatible version.
"""
import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph
from langsmith import traceable

import agents.finance_agent as finance_agent
import agents.hr_agent as hr_agent
import agents.it_agent as it_agent
from agents.approval_agent import approval_manager
from agents.state import AgentState
from db.database import SessionLocal

load_dotenv()

INTENT_LABELS = [
    "hr_policy",
    "hr_leave",
    "it_ticket",
    "it_asset",
    "finance_payslip",
    "finance_reimbursement",
    "finance_tax",
    "unknown",
]

ROLE_INTENT_MAP: dict[str, list[str]] = {
    "employee": ["hr_policy", "hr_leave", "it_ticket", "it_asset", "finance_payslip", "finance_reimbursement", "finance_tax"],
    "manager": ["hr_policy", "hr_leave", "it_ticket", "it_asset", "finance_payslip", "finance_reimbursement", "finance_tax"],
    "hr_team": ["hr_policy", "hr_leave", "it_ticket", "finance_payslip", "finance_reimbursement"],
    "it_team": ["it_ticket", "it_asset", "hr_policy"],
    "finance_team": ["finance_payslip", "finance_reimbursement", "finance_tax", "hr_policy"],
    "admin": INTENT_LABELS,
}

def _detect_intent_node(state: AgentState) -> AgentState:
    """
    Classify user message into intent. Using HumanMessage only for Gemini.
    """
    messages = state.get("messages", [])
    if not messages:
        return {**state, "intent": "unknown"}

    last_user_msg = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage) or (hasattr(m, "type") and m.type == "human"):
            last_user_msg = m.content if hasattr(m, "content") else str(m)
            break

    if not last_user_msg:
        return {**state, "intent": "unknown"}

    # Use a fresh LLM instance for every call to ensure clean state
    llm = ChatGroq(
        model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )
    
    # We use a single HumanMessage with the instructions + the user query.
    # This is the safest way to avoid 'contents is not specified' errors.
    prompt = (
        "Instructions: Classify the user message into exactly ONE category: "
        f"{', '.join(INTENT_LABELS)}.\n\n"
        "Categories:\n"
        "- hr_policy: general HR rules/docs\n"
        "- hr_leave: leave requests/balance\n"
        "- it_ticket: support issues\n"
        "- it_asset: hardware/software requests\n"
        "- finance_payslip: salary questions\n"
        "- finance_reimbursement: expenses\n"
        "- finance_tax: taxes/PF\n"
        "- unknown: anything else\n\n"
        f"User message: \"{last_user_msg}\"\n\n"
        "Respond only with the label."
    )
    
    try:
        # Wrap in a list to ensure 'contents' is provided
        resp = llm.invoke([HumanMessage(content=prompt)])
        intent_raw = resp.content.strip().lower().replace(" ", "_")
        intent = intent_raw if intent_raw in INTENT_LABELS else "unknown"
        return {**state, "intent": intent}
    except Exception as e:
        # If Gemini fails, we default to unknown instead of crashing the whole graph
        print(f"⚠️ Gemini Intent Detection Failed: {e}")
        return {**state, "intent": "unknown", "error": f"Intent detection error: {str(e)}"}

def _validate_role_node(state: AgentState) -> AgentState:
    if state.get("error"): return state
    role = state.get("user_role", "employee")
    intent = state.get("intent", "unknown")
    allowed = ROLE_INTENT_MAP.get(role, [])
    if intent != "unknown" and intent not in allowed:
        return {
            **state,
            "error": "access_denied",
            "final_response": f"Access denied. Your role '{role}' cannot perform '{intent}' actions."
        }
    return state

def _route_to_agent(state: AgentState) -> Literal["hr_node", "it_node", "finance_node", "format_response"]:
    if state.get("error"): return "format_response"
    intent = state.get("intent", "unknown")
    if intent in ("hr_policy", "hr_leave"): return "hr_node"
    if intent in ("it_ticket", "it_asset"): return "it_node"
    if intent in ("finance_payslip", "finance_reimbursement", "finance_tax"): return "finance_node"
    return "format_response"

def build_router_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("detect_intent", _detect_intent_node)
    graph.add_node("validate_role", _validate_role_node)
    graph.add_node("hr_node", lambda s: hr_agent.process(s))
    graph.add_node("it_node", lambda s: it_agent.process(s))
    graph.add_node("finance_node", lambda s: finance_agent.process(s))
    graph.add_node("format_response", _format_response_node)
    
    graph.add_edge(START, "detect_intent")
    graph.add_edge("detect_intent", "validate_role")
    graph.add_conditional_edges("validate_role", _route_to_agent)
    graph.add_edge("hr_node", "format_response")
    graph.add_edge("it_node", "format_response")
    graph.add_edge("finance_node", "format_response")
    graph.add_edge("format_response", END)
    return graph.compile()

def _format_response_node(state: AgentState) -> AgentState:
    res = state.get("final_response", "")
    if not res:
        res = "I couldn't process that. Please try rephrasing."
    return {**state, "final_response": res}

router_graph = build_router_graph()

def run_graph(state: AgentState) -> AgentState:
    return router_graph.invoke(state)
