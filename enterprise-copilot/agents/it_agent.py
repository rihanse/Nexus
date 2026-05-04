"""
IT Agent — ReAct-style LangGraph agent for IT support.
Groq-compatible. Prompts live in agents/prompts/it_prompts.py.
"""
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langsmith import traceable

from agents.prompts import IT_SYSTEM_PROMPT
from agents.state import AgentState
from tools.it_tools import (
    assign_ticket, check_known_outages, create_ticket, get_all_tickets,
    get_my_tickets, get_ticket_status, request_asset, resolve_ticket,
)

load_dotenv()

def _get_it_agent():
    llm = ChatGroq(
        model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )
    tools = [create_ticket, get_ticket_status, get_my_tickets, get_all_tickets,
             assign_ticket, resolve_ticket, request_asset, check_known_outages]
    return create_react_agent(llm, tools)

@traceable(name="it_agent")
def process(state: AgentState) -> AgentState:
    try:
        agent = _get_it_agent()
        messages = list(state["messages"])
        if messages and (isinstance(messages[0], HumanMessage) or getattr(messages[0], "type", "") == "human"):
            ctx = (f"Instructions: {IT_SYSTEM_PROMPT}\n"
                   f"User ID: {state['user_id']}, Name: {state['user_name']}, Role: {state['user_role']}, Dept: {state['user_department']}.\n"
                   f"IMPORTANT: Whenever a tool requires 'user_id' or 'it_engineer_id', you MUST use the exact integer {state['user_id']}.\n\n")
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
        return {**state, "final_response": f"IT Error: {str(e)}"}
