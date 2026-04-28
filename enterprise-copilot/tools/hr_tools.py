"""
HR tools for leave management and policy querying.
"""
import datetime
from typing import Optional

from langchain.tools import tool

import db.crud as crud
from db.database import SessionLocal
from rag.retriever import format_context, retrieve_relevant_docs


def _get_db():
    return SessionLocal()


def _count_working_days(start: datetime.date, end: datetime.date) -> int:
    """Count Mon–Fri working days between start and end inclusive."""
    total = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            total += 1
        current += datetime.timedelta(days=1)
    return total


@tool
def get_leave_balance(user_id: int, leave_type: str) -> str:
    """
    Get leave balance for a specific employee and leave type.

    Args:
        user_id: Employee DB ID.
        leave_type: casual, sick, or annual.

    Returns:
        Formatted leave balance string.
    """
    db = _get_db()
    try:
        balance = crud.get_leave_balance(db, user_id, leave_type)
        if not balance:
            return f"No leave balance found for '{leave_type}'. Please contact HR."
        return (
            f"Leave Balance — {leave_type.title()}:\n"
            f"  Total Allowed : {balance.total_allowed} days\n"
            f"  Used          : {balance.used} days\n"
            f"  Remaining     : {balance.remaining} days\n"
            f"  Year          : {balance.year}"
        )
    finally:
        db.close()


@tool
def apply_leave(user_id: int, leave_type: str, start_date: str, end_date: str, reason: str) -> dict:
    """
    Apply for leave. Validates dates, checks balance and overlaps.

    Args:
        user_id: Employee DB ID.
        leave_type: casual, sick, annual, maternity, paternity.
        start_date: YYYY-MM-DD.
        end_date: YYYY-MM-DD.
        reason: Reason for leave.

    Returns:
        Dict with success, request_id, message, requires_approval.
    """
    db = _get_db()
    try:
        today = datetime.date.today()
        try:
            s = datetime.date.fromisoformat(start_date)
            e = datetime.date.fromisoformat(end_date)
        except ValueError:
            return {"success": False, "message": "Invalid date format. Use YYYY-MM-DD.", "requires_approval": False}
        if s < today:
            return {"success": False, "message": "Start date must be today or future.", "requires_approval": False}
        if e < s:
            return {"success": False, "message": "End date must be on or after start date.", "requires_approval": False}
        overlap = crud.check_overlapping_leave(db, user_id, s, e)
        if overlap:
            return {"success": False, "message": f"Overlapping {overlap.status} leave: {overlap.start_date} → {overlap.end_date}.", "requires_approval": False}
        total_days = _count_working_days(s, e)
        if total_days == 0:
            return {"success": False, "message": "No working days in selected range.", "requires_approval": False}
        if leave_type in ("casual", "sick", "annual"):
            bal = crud.get_leave_balance(db, user_id, leave_type)
            if not bal:
                return {"success": False, "message": f"No balance record for '{leave_type}'.", "requires_approval": False}
            if bal.remaining < total_days:
                return {"success": False, "message": f"Insufficient balance. Remaining: {bal.remaining}, Requested: {total_days}.", "requires_approval": False}
        req = crud.create_leave_request(db, user_id, leave_type, s, e, total_days, reason)
        requires_approval = total_days > 3
        return {
            "success": True,
            "request_id": req.id,
            "message": f"✅ Leave request submitted for {total_days} day(s) from {start_date} to {end_date}.",
            "requires_approval": requires_approval,
        }
    finally:
        db.close()


@tool
def get_leave_history(user_id: int) -> str:
    """
    Get the last 10 leave requests for an employee.

    Args:
        user_id: Employee DB ID.

    Returns:
        Formatted leave history.
    """
    db = _get_db()
    try:
        reqs = crud.get_leave_requests_by_employee(db, user_id)[:10]
        if not reqs:
            return "No leave requests found."
        lines = ["Your Leave History:\n"]
        for r in reqs:
            lines.append(f"  #{r.id} {r.leave_type.title()} | {r.start_date}→{r.end_date} ({r.total_days}d) | {r.status.upper()}")
        return "\n".join(lines)
    finally:
        db.close()


@tool
def cancel_leave(user_id: int, request_id: int) -> str:
    """
    Cancel a pending leave request.

    Args:
        user_id: Employee DB ID.
        request_id: Leave request ID to cancel.

    Returns:
        Confirmation or error message.
    """
    db = _get_db()
    try:
        req = crud.get_leave_request_by_id(db, request_id)
        if not req:
            return f"Leave request #{request_id} not found."
        if req.employee_id != user_id:
            return "You are not authorized to cancel this request."
        if req.status != "pending":
            return f"Only pending requests can be cancelled. Status: '{req.status}'."
        crud.update_leave_status(db, request_id, "cancelled")
        return f"✅ Leave request #{request_id} cancelled."
    finally:
        db.close()


@tool
def get_pending_leave_approvals(manager_id: int) -> str:
    """
    Get all pending leave requests from team members. For managers only.

    Args:
        manager_id: Manager's DB ID.

    Returns:
        Formatted list of pending approvals.
    """
    db = _get_db()
    try:
        reqs = crud.get_pending_approvals_for_manager(db, manager_id)
        if not reqs:
            return "No pending leave approvals for your team."
        lines = ["Pending Approvals:\n"]
        for r in reqs:
            emp = crud.get_user_by_id(db, r.employee_id)
            lines.append(f"  #{r.id} {emp.name if emp else r.employee_id} | {r.leave_type} | {r.start_date}→{r.end_date} | {r.reason}")
        return "\n".join(lines)
    finally:
        db.close()


@tool
def approve_or_reject_leave(manager_id: int, request_id: int, decision: str, comment: str) -> str:
    """
    Approve or reject a leave request as a manager.

    Args:
        manager_id: Manager's DB ID.
        request_id: Leave request ID.
        decision: approved or rejected.
        comment: Reason for decision.

    Returns:
        Confirmation message.
    """
    db = _get_db()
    try:
        if decision not in ("approved", "rejected"):
            return "Decision must be 'approved' or 'rejected'."
        req = crud.get_leave_request_by_id(db, request_id)
        if not req:
            return f"Request #{request_id} not found."
        if req.status != "pending":
            return f"Request is already '{req.status}'."
        emp = crud.get_user_by_id(db, req.employee_id)
        if emp and emp.manager_id != manager_id:
            return "You are not the direct manager of this employee."
        crud.update_leave_status(db, request_id, decision, approver_id=manager_id, comment=comment)
        if decision == "approved":
            crud.update_leave_balance(db, req.employee_id, req.leave_type, req.total_days)
        return f"✅ Request #{request_id} {decision.upper()}. Comment: {comment}"
    finally:
        db.close()


@tool
def query_hr_policy(question: str, user_role: str) -> str:
    """
    Answer an HR policy question using the RAG knowledge base.

    Args:
        question: HR policy question.
        user_role: Role of the requesting user (for RBAC filtering).

    Returns:
        Formatted answer with source citations.
    """
    docs = retrieve_relevant_docs(question, user_role, department="HR", k=4)
    if not docs:
        return "No HR policy info found. Contact hr@company.com."
    context = format_context(docs)
    sources = list({d["source"] for d in docs})
    return f"Based on company HR policy:\n\n{context}\n\n📎 Sources: {', '.join(sources)}"
