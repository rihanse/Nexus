"""
Email notification tools using Power Automate HTTP triggers.
"""
import datetime
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

POWER_AUTOMATE_URL: str = os.getenv("POWER_AUTOMATE_URL", "")
logger = logging.getLogger(__name__)


def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    """Send an email via Power Automate HTTP trigger. Returns True on success."""
    if not POWER_AUTOMATE_URL or POWER_AUTOMATE_URL == "your_power_automate_http_trigger_url_here":
        logger.warning("[%s] Email skipped (no URL). To: %s | Subject: %s",
                       datetime.datetime.utcnow().isoformat(), to_email, subject)
        return False
    try:
        resp = httpx.post(POWER_AUTOMATE_URL, json={"to": to_email, "subject": subject, "body": body}, timeout=10)
        success = resp.status_code in (200, 202)
        logger.info("[%s] Email %s | To: %s | HTTP %d",
                    datetime.datetime.utcnow().isoformat(), "sent" if success else "failed", to_email, resp.status_code)
        return success
    except Exception as exc:
        logger.error("[%s] Email error: %s", datetime.datetime.utcnow().isoformat(), exc)
        return False


def send_leave_request_email(employee_name: str, manager_email: str, leave_type: str,
                              start_date: str, end_date: str, days: int, request_id: int) -> bool:
    """Notify manager of a pending leave approval."""
    subject = f"Leave Request Pending Approval — {employee_name} [{leave_type.title()}]"
    body = (
        f"Dear Manager,\n\n{employee_name} has submitted a leave request.\n\n"
        f"  Leave Type : {leave_type.title()}\n  From       : {start_date}\n"
        f"  To         : {end_date}\n  Days       : {days}\n  Request ID : #{request_id}\n\n"
        f"Please log in to the Enterprise Copilot to approve or reject.\n\nRegards,\nEnterprise HR Copilot"
    )
    return send_email_notification(manager_email, subject, body)


def send_leave_decision_email(employee_email: str, decision: str, leave_type: str,
                               start_date: str, end_date: str, comment: str) -> bool:
    """Notify employee of leave approval/rejection."""
    status = "APPROVED ✅" if decision == "approved" else "REJECTED ❌"
    subject = f"Your Leave Request Has Been {decision.upper()}"
    body = (
        f"Dear Employee,\n\nYour leave request has been {status}.\n\n"
        f"  Leave Type : {leave_type.title()}\n  From       : {start_date}\n"
        f"  To         : {end_date}\n  Decision   : {decision.upper()}\n"
        f"  Comment    : {comment}\n\nRegards,\nEnterprise HR Copilot"
    )
    return send_email_notification(employee_email, subject, body)


def send_ticket_created_email(employee_email: str, ticket_number: str, issue_type: str, title: str) -> bool:
    """Confirm IT ticket creation to the employee."""
    subject = f"IT Ticket Created — {ticket_number}"
    body = (
        f"Dear Employee,\n\nYour IT ticket has been created.\n\n"
        f"  Ticket : {ticket_number}\n  Type   : {issue_type.title()}\n"
        f"  Title  : {title}\n  Status : OPEN\n\n"
        f"Our IT team will respond per SLA.\nContact it@company.com for urgent issues.\n\nRegards,\nEnterprise IT Copilot"
    )
    return send_email_notification(employee_email, subject, body)


def send_ticket_resolved_email(employee_email: str, ticket_number: str, resolution_notes: str) -> bool:
    """Notify employee that their ticket has been resolved."""
    subject = f"IT Ticket Resolved — {ticket_number}"
    body = (
        f"Dear Employee,\n\nTicket {ticket_number} has been resolved.\n\n"
        f"  Resolution: {resolution_notes}\n\n"
        f"If the issue persists, raise a new ticket referencing {ticket_number}.\n\nRegards,\nEnterprise IT Copilot"
    )
    return send_email_notification(employee_email, subject, body)
