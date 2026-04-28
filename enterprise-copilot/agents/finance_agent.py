"""
Finance Agent — ReAct-style LangGraph agent for finance support.
Gemini-compatible.
"""
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langsmith import traceable

from agents.state import AgentState
from tools.finance_tools import (
    get_latest_payslip, get_reimbursement_status, get_tax_info, submit_reimbursement,
)

load_dotenv()

FINANCE_SYSTEM_PROMPT = "You are the Finance Assistant. Help with payslips, taxes, and reimbursements. Be precise."

def _get_finance_agent():
    llm = ChatGroq(
        model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )
    tools = [get_latest_payslip, submit_reimbursement, get_reimbursement_status, get_tax_info]
    return create_react_agent(llm, tools)

@traceable(name="finance_agent")
def process(state: AgentState) -> AgentState:
    try:
        agent = _get_finance_agent()
        messages = list(state["messages"])
        if messages and (isinstance(messages[0], HumanMessage) or getattr(messages[0], "type", "") == "human"):
            ctx = (f"Instructions: {FINANCE_SYSTEM_PROMPT}\n"
                   f"User ID: {state['user_id']}, Name: {state['user_name']}, Role: {state['user_role']}, Dept: {state['user_department']}.\n"
                   f"IMPORTANT: Whenever a tool requires 'user_id', you MUST use the exact integer {state['user_id']}.\n\n")
            messages[0] = HumanMessage(content=ctx + messages[0].content)
        
        clean_messages = [m for m in messages if getattr(m, "type", "") != "system"]
        if not clean_messages: clean_messages = [HumanMessage(content="Hello")]

        result = agent.invoke({"messages": clean_messages})
        last_msg = result["messages"][-1]
        
        return {
            **state,
            "messages": result["messages"],
            "final_response": last_msg.content if hasattr(last_msg, "content") else str(last_msg),
            "requires_approval": "requires_approval" in str(result).lower()
        }
    except Exception as e:
        return {**state, "final_response": f"Finance Error: {str(e)}"}
