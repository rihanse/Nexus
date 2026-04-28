"""
FastMCP server exposing Enterprise Copilot tools on port 8001.
"""
from fastmcp import FastMCP

from db.database import SessionLocal
from tools.finance_tools import (
    get_latest_payslip,
    submit_reimbursement,
)
from tools.hr_tools import (
    apply_leave,
    cancel_leave,
    get_leave_balance,
    get_leave_history,
)
from tools.it_tools import (
    create_ticket,
    get_ticket_status,
    request_asset,
)

mcp = FastMCP("Enterprise Copilot Tools")


# ─────────────────────────────────────────────
# HR Tools
# ─────────────────────────────────────────────

@mcp.tool()
def mcp_apply_leave(user_id: int, leave_type: str, start_date: str, end_date: str, reason: str) -> dict:
    """
    Apply for a leave request.

    Args:
        user_id: Employee DB ID.
        leave_type: casual, sick, annual, maternity, or paternity.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        reason: Reason for the leave.

    Returns:
        Dict with success, request_id, message, requires_approval.
    """
    return apply_leave.invoke(
        {"user_id": user_id, "leave_type": leave_type, "start_date": start_date, "end_date": end_date, "reason": reason}
    )


@mcp.tool()
def mcp_get_leave_balance(user_id: int, leave_type: str) -> str:
    """
    Get leave balance for an employee.

    Args:
        user_id: Employee DB ID.
        leave_type: casual, sick, or annual.

    Returns:
        Formatted leave balance string.
    """
    return get_leave_balance.invoke({"user_id": user_id, "leave_type": leave_type})


@mcp.tool()
def mcp_get_leave_history(user_id: int) -> str:
    """
    Get last 10 leave requests for an employee.

    Args:
        user_id: Employee DB ID.

    Returns:
        Formatted leave history string.
    """
    return get_leave_history.invoke({"user_id": user_id})


@mcp.tool()
def mcp_cancel_leave(user_id: int, request_id: int) -> str:
    """
    Cancel a pending leave request.

    Args:
        user_id: Employee DB ID.
        request_id: Leave request ID to cancel.

    Returns:
        Confirmation message.
    """
    return cancel_leave.invoke({"user_id": user_id, "request_id": request_id})


# ─────────────────────────────────────────────
# IT Tools
# ─────────────────────────────────────────────

@mcp.tool()
def mcp_create_ticket(user_id: int, issue_type: str, title: str, description: str, priority: str) -> dict:
    """
    Create an IT support ticket.

    Args:
        user_id: Employee DB ID.
        issue_type: laptop, vpn, email, printer, network, or software.
        title: Short issue title.
        description: Detailed description.
        priority: low, medium, high, or critical.

    Returns:
        Dict with success, ticket_id, ticket_number, message.
    """
    return create_ticket.invoke(
        {"user_id": user_id, "issue_type": issue_type, "title": title, "description": description, "priority": priority}
    )


@mcp.tool()
def mcp_get_ticket_status(user_id: int, ticket_id: int) -> str:
    """
    Get the status of an IT ticket.

    Args:
        user_id: Requesting employee DB ID.
        ticket_id: Ticket primary key.

    Returns:
        Formatted ticket status string.
    """
    return get_ticket_status.invoke({"user_id": user_id, "ticket_id": ticket_id})


@mcp.tool()
def mcp_request_asset(user_id: int, asset_type: str, asset_name: str, justification: str) -> dict:
    """
    Submit a hardware or software asset request.

    Args:
        user_id: Employee DB ID.
        asset_type: laptop, monitor, keyboard, mouse, vpn_token, or software_license.
        asset_name: Specific name or model.
        justification: Business justification.

    Returns:
        Dict with success, request_id, message, requires_approval.
    """
    return request_asset.invoke(
        {"user_id": user_id, "asset_type": asset_type, "asset_name": asset_name, "justification": justification}
    )


# ─────────────────────────────────────────────
# Finance Tools
# ─────────────────────────────────────────────

@mcp.tool()
def mcp_get_latest_payslip(user_id: int) -> str:
    """
    Get the most recent payslip for an employee.

    Args:
        user_id: Employee DB ID.

    Returns:
        Formatted payslip string.
    """
    return get_latest_payslip.invoke({"user_id": user_id})


@mcp.tool()
def mcp_submit_reimbursement(user_id: int, expense_type: str, amount: float, description: str) -> dict:
    """
    Submit a reimbursement claim.

    Args:
        user_id: Employee DB ID.
        expense_type: travel, internet, food, or client_meeting.
        amount: Amount in INR.
        description: Expense description.

    Returns:
        Dict with success, reimbursement_id, message, requires_approval.
    """
    return submit_reimbursement.invoke(
        {"user_id": user_id, "expense_type": expense_type, "amount": amount, "description": description}
    )


if __name__ == "__main__":
    mcp.run(port=8001)
