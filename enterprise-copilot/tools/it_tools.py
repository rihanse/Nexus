"""
IT support tools for ticket management, asset requests, and outage checking.
"""
import datetime

from langchain.tools import tool

import db.crud as crud
from db.database import SessionLocal
from db.models import ITTicket


def _get_db():
    return SessionLocal()


@tool
def create_ticket(user_id: int, issue_type: str, title: str, description: str, priority: str) -> dict:
    """
    Create an IT support ticket. Checks for known outages and duplicate open tickets first.

    Args:
        user_id: Employee DB ID.
        issue_type: laptop, vpn, email, printer, network, or software.
        title: Short issue title.
        description: Detailed description.
        priority: low, medium, high, or critical.

    Returns:
        Dict with success, ticket_id, ticket_number, message, outage_active.
    """
    db = _get_db()
    try:
        outages = crud.get_active_outages(db)
        matching = [o for o in outages if issue_type.lower() in o.service.lower()]
        if matching:
            o = matching[0]
            return {
                "success": False, "ticket_id": None, "ticket_number": None, "outage_active": True,
                "message": f"⚠️ Known Outage for '{issue_type}':\n{o.description}\nStarted: {o.start_time.strftime('%Y-%m-%d %H:%M')} UTC\nOur team is working on it.",
            }
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        dup = db.query(ITTicket).filter(
            ITTicket.employee_id == user_id,
            ITTicket.issue_type == issue_type,
            ITTicket.status.in_(["open", "in_progress"]),
            ITTicket.created_at >= cutoff,
        ).first()
        if dup:
            return {
                "success": False, "ticket_id": dup.id, "ticket_number": dup.ticket_number, "outage_active": False,
                "message": f"You already have an open '{issue_type}' ticket: {dup.ticket_number} | Status: {dup.status.upper()}. Please track this existing ticket.",
            }
        t = crud.create_ticket(db, user_id, issue_type, title, description, priority)
        return {
            "success": True, "ticket_id": t.id, "ticket_number": t.ticket_number, "outage_active": False,
            "message": f"✅ Ticket {t.ticket_number} created!\n  Title: {title} | Priority: {priority.upper()} | Status: OPEN",
        }
    finally:
        db.close()


@tool
def get_ticket_status(user_id: int, ticket_id: int) -> str:
    """
    Get status of a specific IT ticket. Employees can only view their own tickets.

    Args:
        user_id: Requesting employee DB ID.
        ticket_id: Ticket primary key.

    Returns:
        Formatted ticket status string.
    """
    db = _get_db()
    try:
        t = crud.get_ticket_by_id(db, ticket_id)
        if not t:
            return f"Ticket #{ticket_id} not found."
        if t.employee_id != user_id:
            return "Access denied. You can only view your own tickets."
        lines = [
            f"Ticket {t.ticket_number}:",
            f"  Title    : {t.title}",
            f"  Type     : {t.issue_type.title()}",
            f"  Priority : {t.priority.upper()}",
            f"  Status   : {t.status.upper()}",
            f"  Created  : {t.created_at.strftime('%Y-%m-%d')}",
        ]
        if t.resolution_notes:
            lines.append(f"  Resolution: {t.resolution_notes}")
        return "\n".join(lines)
    finally:
        db.close()


@tool
def get_my_tickets(user_id: int) -> str:
    """
    Get all IT tickets raised by the current user.

    Args:
        user_id: Employee DB ID.

    Returns:
        Formatted ticket list.
    """
    db = _get_db()
    try:
        tickets = crud.get_tickets_by_employee(db, user_id)
        if not tickets:
            return "You have no IT tickets."
        lines = [f"Your IT Tickets ({len(tickets)}):\n"]
        for t in tickets:
            lines.append(f"  [{t.ticket_number}] {t.title} | {t.issue_type.title()} | {t.priority.upper()} | {t.status.upper()} | {t.created_at.strftime('%Y-%m-%d')}")
        return "\n".join(lines)
    finally:
        db.close()


@tool
def get_all_tickets(requesting_user_id: int) -> str:
    """
    Get all IT tickets in the system. Restricted to IT team and admin.

    Args:
        requesting_user_id: DB ID of the IT team member.

    Returns:
        Formatted list of all tickets.
    """
    db = _get_db()
    try:
        user = crud.get_user_by_id(db, requesting_user_id)
        if not user or user.role not in ("it_team", "admin"):
            return "Access denied. Only IT team members can view all tickets."
        tickets = crud.get_all_tickets(db)
        if not tickets:
            return "No tickets in the system."
        lines = [f"All Tickets ({len(tickets)}):\n"]
        for t in tickets:
            emp = crud.get_user_by_id(db, t.employee_id)
            lines.append(f"  [{t.ticket_number}] {t.title} | {emp.name if emp else t.employee_id} | {t.issue_type.title()} | {t.priority.upper()} | {t.status.upper()}")
        return "\n".join(lines)
    finally:
        db.close()


@tool
def assign_ticket(it_engineer_id: int, ticket_id: int) -> str:
    """
    Assign a ticket to the calling IT engineer. IT team only.

    Args:
        it_engineer_id: DB ID of the IT engineer.
        ticket_id: Ticket to assign.

    Returns:
        Confirmation message.
    """
    db = _get_db()
    try:
        user = crud.get_user_by_id(db, it_engineer_id)
        if not user or user.role not in ("it_team", "admin"):
            return "Access denied. Only IT team members can assign tickets."
        t = crud.assign_ticket(db, ticket_id, it_engineer_id)
        if not t:
            return f"Ticket #{ticket_id} not found."
        return f"✅ {t.ticket_number} assigned to {user.name}. Status: IN_PROGRESS"
    finally:
        db.close()


@tool
def resolve_ticket(it_engineer_id: int, ticket_id: int, resolution_notes: str) -> str:
    """
    Mark a ticket as resolved. IT team only.

    Args:
        it_engineer_id: DB ID of the IT engineer.
        ticket_id: Ticket to resolve.
        resolution_notes: How the issue was resolved.

    Returns:
        Confirmation message.
    """
    db = _get_db()
    try:
        user = crud.get_user_by_id(db, it_engineer_id)
        if not user or user.role not in ("it_team", "admin"):
            return "Access denied. Only IT team members can resolve tickets."
        t = crud.update_ticket_status(db, ticket_id, "resolved", resolution_notes)
        if not t:
            return f"Ticket #{ticket_id} not found."
        return f"✅ {t.ticket_number} marked RESOLVED.\n  Notes: {resolution_notes}"
    finally:
        db.close()


@tool
def request_asset(user_id: int, asset_type: str, asset_name: str, justification: str) -> dict:
    """
    Submit a hardware or software asset request requiring manager approval.

    Args:
        user_id: Employee DB ID.
        asset_type: laptop, monitor, keyboard, mouse, vpn_token, or software_license.
        asset_name: Specific name or model.
        justification: Business justification.

    Returns:
        Dict with success, request_id, message, requires_approval.
    """
    db = _get_db()
    try:
        req = crud.create_asset_request(db, user_id, asset_type, asset_name, justification)
        return {
            "success": True, "request_id": req.id, "requires_approval": True,
            "message": f"✅ Asset request submitted!\n  Asset: {asset_name} ({asset_type})\n  Status: Pending Manager Approval",
        }
    finally:
        db.close()


@tool
def check_known_outages(issue_type: str) -> str:
    """
    Check for any active known outage for a service type.

    Args:
        issue_type: Service to check e.g. vpn, email, network.

    Returns:
        Outage details or confirmation that none exist.
    """
    db = _get_db()
    try:
        outages = crud.get_active_outages(db)
        relevant = [o for o in outages if issue_type.lower() in o.service.lower()]
        if not relevant:
            return f"No known active outages for '{issue_type}'. You may raise a ticket."
        lines = [f"⚠️ Active Outage(s) for '{issue_type}':\n"]
        for o in relevant:
            lines.append(f"  {o.service}: {o.description}")
            lines.append(f"  Since: {o.start_time.strftime('%Y-%m-%d %H:%M')} UTC")
        return "\n".join(lines)
    finally:
        db.close()
