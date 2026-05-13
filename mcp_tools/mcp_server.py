import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP

from tools.hr_tools import (
    get_leave_balance,
    apply_leave,
    approve_leave,
    reject_leave,
    get_pending_leaves
)

from tools.it_tools import (
    create_ticket,
    get_ticket_status,
    request_asset,
    get_asset_status,
    manager_approve_asset,
    it_approve_asset
)

from tools.finance_tools import (
    submit_reimbursement,
    get_reimbursement_status,
    approve_reimbursement,
    reject_reimbursement
)

from rag.retriever import answer_policy_question


mcp = FastMCP("Workplace Buddy MCP Server")


@mcp.tool()
def health_check() -> dict:
    """
    Checks whether the Workplace Buddy MCP server is running.
    """
    return {
        "success": True,
        "message": "Workplace Buddy MCP server is running."
    }


# -------------------------
# HR TOOLS
# -------------------------

@mcp.tool()
def get_leave_balance_mcp(emp_id: str) -> dict:
    """
    Get leave balance for an employee.
    """
    return get_leave_balance(emp_id)


@mcp.tool()
def apply_leave_mcp(
    emp_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str
) -> dict:
    """
    Apply leave for an employee.
    Dates must be in YYYY-MM-DD format.
    Leave type must be casual, sick, or earned.
    """
    return apply_leave(
        emp_id=emp_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason
    )


@mcp.tool()
def approve_leave_mcp(
    request_id: int,
    approver_role: str,
    comment: str = "Approved through MCP"
) -> dict:
    """
    Approve a leave request.
    Only manager, HR, or admin roles are allowed.
    """
    return approve_leave(
        request_id=request_id,
        approver_role=approver_role,
        comment=comment
    )


@mcp.tool()
def reject_leave_mcp(
    request_id: int,
    approver_role: str,
    comment: str = "Rejected through MCP"
) -> dict:
    """
    Reject a leave request.
    Only manager, HR, or admin roles are allowed.
    """
    return reject_leave(
        request_id=request_id,
        approver_role=approver_role,
        comment=comment
    )


@mcp.tool()
def get_pending_leaves_mcp(role: str) -> dict:
    """
    Get pending leave requests.
    Only manager, HR, or admin roles are allowed.
    """
    return get_pending_leaves(role)


# -------------------------
# IT TICKET TOOLS
# -------------------------

@mcp.tool()
def create_it_ticket_mcp(
    emp_id: str,
    issue_type: str,
    description: str,
    priority: str = "medium"
) -> dict:
    """
    Create an IT support ticket.
    Before creating a ticket, the tool checks known outages, maintenance, and duplicate tickets.
    """
    return create_ticket(
        emp_id=emp_id,
        issue_type=issue_type,
        description=description,
        priority=priority
    )


@mcp.tool()
def get_ticket_status_mcp(
    emp_id: str,
    role: str,
    ticket_id: int | None = None
) -> dict:
    """
    Get IT ticket status.
    Employees can view own tickets.
    IT/Admin can view all tickets.
    """
    return get_ticket_status(
        emp_id=emp_id,
        role=role,
        ticket_id=ticket_id
    )


# -------------------------
# ASSET TOOLS
# -------------------------

@mcp.tool()
def request_asset_mcp(
    emp_id: str,
    asset_type: str,
    reason: str
) -> dict:
    """
    Request an IT asset such as laptop, monitor, keyboard, mouse, VPN token, or software license.
    """
    return request_asset(
        emp_id=emp_id,
        asset_type=asset_type,
        reason=reason
    )


@mcp.tool()
def get_asset_status_mcp(
    emp_id: str,
    role: str,
    request_id: int | None = None
) -> dict:
    """
    Get asset request status.
    Employees can view own asset requests.
    Manager, IT, and Admin can view broader asset requests.
    """
    return get_asset_status(
        emp_id=emp_id,
        role=role,
        request_id=request_id
    )


@mcp.tool()
def manager_approve_asset_mcp(
    request_id: int,
    role: str
) -> dict:
    """
    Manager-level approval for asset requests.
    Only manager or admin roles are allowed.
    """
    return manager_approve_asset(
        request_id=request_id,
        role=role
    )


@mcp.tool()
def it_approve_asset_mcp(
    request_id: int,
    role: str
) -> dict:
    """
    IT-level approval and inventory validation for asset requests.
    Only IT or admin roles are allowed.
    """
    return it_approve_asset(
        request_id=request_id,
        role=role
    )


# -------------------------
# FINANCE TOOLS
# -------------------------

@mcp.tool()
def submit_reimbursement_mcp(
    emp_id: str,
    claim_type: str,
    amount: float,
    description: str
) -> dict:
    """
    Submit a reimbursement request.
    Claim type can be travel, internet, food, client meeting, or other.
    """
    return submit_reimbursement(
        emp_id=emp_id,
        claim_type=claim_type,
        amount=amount,
        description=description
    )


@mcp.tool()
def get_reimbursement_status_mcp(
    emp_id: str,
    role: str,
    reimbursement_id: int | None = None
) -> dict:
    """
    Get reimbursement status.
    Employees can view own reimbursements.
    Finance/Admin can view broader reimbursement requests.
    """
    return get_reimbursement_status(
        emp_id=emp_id,
        role=role,
        reimbursement_id=reimbursement_id
    )


@mcp.tool()
def approve_reimbursement_mcp(
    reimbursement_id: int,
    role: str,
    comment: str = "Approved through MCP"
) -> dict:
    """
    Approve a reimbursement request.
    Only finance or admin roles are allowed.
    """
    return approve_reimbursement(
        reimbursement_id=reimbursement_id,
        role=role,
        comment=comment
    )


@mcp.tool()
def reject_reimbursement_mcp(
    reimbursement_id: int,
    role: str,
    comment: str = "Rejected through MCP"
) -> dict:
    """
    Reject a reimbursement request.
    Only finance or admin roles are allowed.
    """
    return reject_reimbursement(
        reimbursement_id=reimbursement_id,
        role=role,
        comment=comment
    )


# -------------------------
# RAG TOOL
# -------------------------

@mcp.tool()
def ask_policy_question_mcp(
    question: str,
    role: str = "employee"
) -> dict:
    """
    Ask a policy question using the internal RAG system.
    """
    return answer_policy_question(
        question=question,
        role=role,
        k=3
    )


if __name__ == "__main__":
    mcp.run()