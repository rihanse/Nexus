"""
Approval Manager — handles pending approvals for leave, assets, and reimbursements.
"""
import datetime
from typing import Optional

import db.crud as crud
from db.database import SessionLocal
from tools.email_tools import (
    send_leave_decision_email,
    send_ticket_resolved_email,
)


class ApprovalManager:
    """
    Manages the lifecycle of approval requests across leave, asset, and reimbursement domains.
    Uses an in-memory registry of pending approvals keyed by request type + ID.
    """

    def __init__(self) -> None:
        """Initialize the in-memory pending approvals store."""
        # Structure: {approval_id: {type, request_id, employee_id, approver_id, created_at}}
        self._pending: dict[int, dict] = {}
        self._next_id: int = 1

    def create_pending_approval(
        self,
        request_type: str,
        request_id: int,
        employee_id: int,
        approver_id: int,
        db=None,
    ) -> int:
        """
        Register a new pending approval record.

        Args:
            request_type: Type of request ('leave', 'asset', 'reimbursement').
            request_id: DB ID of the underlying request.
            employee_id: DB ID of the employee who made the request.
            approver_id: DB ID of the user who should approve.
            db: Optional DB session (unused, kept for interface consistency).

        Returns:
            The approval_id assigned to this pending approval.
        """
        approval_id = self._next_id
        self._pending[approval_id] = {
            "approval_id": approval_id,
            "request_type": request_type,
            "request_id": request_id,
            "employee_id": employee_id,
            "approver_id": approver_id,
            "status": "pending",
            "created_at": datetime.datetime.utcnow().isoformat(),
        }
        self._next_id += 1
        return approval_id

    def get_pending_approvals(self, approver_id: int, db=None) -> list[dict]:
        """
        Get all pending approvals assigned to a specific approver.

        Args:
            approver_id: DB ID of the approver.
            db: Optional DB session.

        Returns:
            List of pending approval dicts.
        """
        return [
            record
            for record in self._pending.values()
            if record["approver_id"] == approver_id and record["status"] == "pending"
        ]

    def process_approval(
        self,
        approval_id: int,
        decision: str,
        comment: str,
        approver_id: int,
        db=None,
    ) -> dict:
        """
        Process an approval decision and update the underlying DB record.
        Also sends email notifications to the affected employee.

        Args:
            approval_id: ID of the pending approval to process.
            decision: 'approved' or 'rejected'.
            comment: Comment from the approver.
            approver_id: DB ID of the approver (for validation).
            db: Optional SQLAlchemy session. If None, creates its own.

        Returns:
            Dict with success (bool), message (str), and request_type (str).
        """
        if approval_id not in self._pending:
            return {"success": False, "message": f"Approval #{approval_id} not found."}

        record = self._pending[approval_id]
        if record["approver_id"] != approver_id:
            return {"success": False, "message": "You are not authorized to process this approval."}
        if record["status"] != "pending":
            return {"success": False, "message": f"Approval #{approval_id} is already '{record['status']}'."}
        if decision not in ("approved", "rejected"):
            return {"success": False, "message": "Decision must be 'approved' or 'rejected'."}

        session = db if db else SessionLocal()
        close_session = db is None
        try:
            request_type = record["request_type"]
            request_id = record["request_id"]
            employee_id = record["employee_id"]

            emp = crud.get_user_by_id(session, employee_id)
            emp_email = emp.email if emp else None
            emp_name = emp.name if emp else f"Employee #{employee_id}"

            if request_type == "leave":
                leave_req = crud.get_leave_request_by_id(session, request_id)
                crud.update_leave_status(session, request_id, decision, approver_id=approver_id, comment=comment)
                if decision == "approved" and leave_req:
                    crud.update_leave_balance(session, employee_id, leave_req.leave_type, leave_req.total_days)
                if emp_email and leave_req:
                    send_leave_decision_email(
                        emp_email,
                        decision,
                        leave_req.leave_type,
                        str(leave_req.start_date),
                        str(leave_req.end_date),
                        comment,
                    )

            elif request_type == "asset":
                crud.update_asset_status(
                    session,
                    request_id,
                    decision,
                    manager_approval=decision,
                )

            elif request_type == "reimbursement":
                crud.update_reimbursement_status(session, request_id, decision, approver_id=approver_id)

            # Mark approval as processed
            record["status"] = decision
            record["processed_at"] = datetime.datetime.utcnow().isoformat()
            record["comment"] = comment

            return {
                "success": True,
                "request_type": request_type,
                "message": (
                    f"Approval #{approval_id} processed: {decision.upper()}.\n"
                    f"  Type: {request_type} | Request ID: #{request_id}\n"
                    f"  Employee: {emp_name} | Comment: {comment}"
                ),
            }
        except Exception as exc:
            return {"success": False, "message": f"Error processing approval: {str(exc)}"}
        finally:
            if close_session:
                session.close()


# Singleton instance for use across the application
approval_manager = ApprovalManager()
