"""
HR Agent — ReAct-style LangGraph agent for HR queries and leave management.
Gemini-compatible: no SystemMessage, context injected into HumanMessage.
"""
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langsmith import traceable

from agents.state import AgentState
from tools.hr_tools import (
    apply_leave,
    approve_or_reject_leave,
    cancel_leave,
    get_leave_balance,
    get_leave_history,
    get_pending_leave_approvals,
    query_hr_policy,
)

load_dotenv()

HR_SYSTEM_PROMPT = (
    "You are the HR Assistant. Help with policies, leave, and queries. "
    "Confirm leave details before submitting. Professionally handle requests."
)

def _get_hr_agent():
    llm = ChatGroq(
        model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )
    tools = [get_leave_balance, apply_leave, get_leave_history, cancel_leave, 
             get_pending_leave_approvals, approve_or_reject_leave, query_hr_policy]
    return create_react_agent(llm, tools)

@traceable(name="hr_agent")
def process(state: AgentState) -> AgentState:
    try:
        agent = _get_hr_agent()
        
        # Inject system prompt and user context into the FIRST message if it's a HumanMessage
        messages = list(state["messages"])
        if messages and (isinstance(messages[0], HumanMessage) or getattr(messages[0], "type", "") == "human"):
            ctx = (f"Instructions: {HR_SYSTEM_PROMPT}\n"
                   f"User ID: {state['user_id']}, Name: {state['user_name']}, Role: {state['user_role']}, Dept: {state['user_department']}.\n"
                   f"IMPORTANT: Whenever a tool requires 'user_id', you MUST use the exact integer {state['user_id']}.\n\n")
            messages[0] = HumanMessage(content=ctx + messages[0].content)
        
        # Filter out any SystemMessages that might have snuck in
        clean_messages = [m for m in messages if getattr(m, "type", "") != "system"]
        
        if not clean_messages:
            clean_messages = [HumanMessage(content="Hello")]

        result = agent.invoke({"messages": clean_messages})
        last_msg = result["messages"][-1]
        
        return {
            **state,
            "messages": result["messages"],
            "final_response": last_msg.content if hasattr(last_msg, "content") else str(last_msg),
            "requires_approval": "requires_approval" in str(result).lower()
        }
    except Exception as e:
        return {**state, "final_response": f"HR Error: {str(e)}"}
