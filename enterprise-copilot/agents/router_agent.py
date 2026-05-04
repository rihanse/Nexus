"""
Router Agent — main LangGraph supervisor that classifies intent and routes to domain agents.
Groq-compatible version. Prompts live in agents/prompts/router_prompts.py.
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
from agents.prompts import INTENT_DETECTION_PROMPT_TEMPLATE
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
    prompt = INTENT_DETECTION_PROMPT_TEMPLATE.format(
        intent_labels=", ".join(INTENT_LABELS),
        user_message=last_user_msg,
    )
    
    try:
        # Wrap in a list to ensure 'contents' is provided
        resp = llm.invoke([HumanMessage(content=prompt)])
        intent_raw = resp.content.strip().lower().replace(" ", "_")
        intent = intent_raw if intent_raw in INTENT_LABELS else "unknown"
        return {**state, "intent": intent}
    except Exception as e:
        # If Gemini fails, we default to unknown instead of crashing the whole graph
        print(f"[WARN] Intent Detection Failed: {e}")
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

import ast
from agents.approval_agent import approval_manager
from db.database import SessionLocal
import db.crud as crud

def _format_response_node(state: AgentState) -> AgentState:
    res = state.get("final_response", "")
    if not res:
        res = "I couldn't process that. Please try rephrasing."
    
    # Check for approvals triggered in tool messages
    requires_approval = False
    for m in state.get("messages", []):
        if getattr(m, "type", "") == "tool":
            try:
                # Tools often return stringified dicts
                data = ast.literal_eval(m.content)
                if isinstance(data, dict) and data.get("requires_approval"):
                    # Check for various ID keys used by different tools
                    req_id = data.get("request_id") or data.get("reimbursement_id") or data.get("ticket_id") or data.get("leave_id")
                    name = getattr(m, "name", "")
                    atype = "leave" if "leave" in name else "asset" if "asset" in name else "reimbursement" if "reimb" in name else "unknown"
                    
                    if req_id:
                        db = SessionLocal()
                        user = crud.get_user_by_id(db, state["user_id"])
                        manager_id = user.manager_id if user and user.manager_id else state["user_id"]
                        
                        approval_manager.create_pending_approval(
                            request_type=atype,
                            request_id=req_id,
                            employee_id=state["user_id"],
                            approver_id=manager_id,
                            db=db
                        )
                        db.close()
                        requires_approval = True
            except Exception:
                pass

    return {**state, "final_response": res, "requires_approval": requires_approval}

router_graph = build_router_graph()

def run_graph(state: AgentState) -> AgentState:
    return router_graph.invoke(state)
