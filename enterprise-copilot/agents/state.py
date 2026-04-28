"""
LangGraph AgentState definition for the Enterprise Copilot multi-agent system.
"""
from typing import Annotated, Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    Shared state passed between all nodes in the LangGraph router graph.

    Fields:
        messages: Full conversation history, managed by add_messages reducer.
        user_id: DB primary key of the authenticated user.
        user_role: Role string (employee, manager, hr_team, it_team, finance_team, admin).
        user_department: Department of the user (Engineering, HR, IT, Finance, etc.).
        user_name: Full name of the user.
        user_email: Email address of the user.
        intent: Detected intent from router (hr_policy, hr_leave, it_ticket, etc.).
        current_agent: Which agent is currently handling the request.
        requires_approval: True if the action requires manager/team approval.
        approval_request_id: DB ID of the pending approval record if applicable.
        approval_type: Type of approval needed (leave, asset, reimbursement).
        final_response: The formatted response to send back to the user.
        error: Any error message to surface to the user.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    user_id: int
    user_role: str
    user_department: str
    user_name: str
    user_email: str
    intent: str
    current_agent: str
    requires_approval: bool
    approval_request_id: Optional[int]
    approval_type: Optional[str]
    final_response: str
    error: Optional[str]
