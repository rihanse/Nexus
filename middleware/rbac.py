from database.db import get_connection


def get_user_role(emp_id: str) -> str | None:
    """
    Gets role of a user from the users table.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT role
    FROM users
    WHERE emp_id = ?
    """, (emp_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return row["role"]


def normalize_role(role: str) -> str:
    return role.lower().strip()


def can_approve_leave(role: str) -> bool:
    return normalize_role(role) in ["manager", "hr", "admin"]


def can_view_pending_leaves(role: str) -> bool:
    return normalize_role(role) in ["manager", "hr", "admin"]


def can_view_all_tickets(role: str) -> bool:
    return normalize_role(role) in ["it", "admin"]


def can_assign_ticket(role: str) -> bool:
    return normalize_role(role) in ["it", "admin"]


def can_resolve_ticket(role: str) -> bool:
    return normalize_role(role) in ["it", "admin"]


def can_manager_approve_asset(role: str) -> bool:
    return normalize_role(role) in ["manager", "admin"]


def can_it_approve_asset(role: str) -> bool:
    return normalize_role(role) in ["it", "admin"]


def can_approve_reimbursement(role: str) -> bool:
    return normalize_role(role) in ["finance", "admin"]


def validate_intent_access(intent: str, role: str) -> dict:
    """
    Central role-based access control validator.
    This checks whether a role is allowed to perform an intent.
    """

    role = normalize_role(role)

    # General actions allowed for all authenticated users
    allowed_for_all = [
        "small_talk",
        "rag",
        "chat_history",
        "apply_leave",
        "leave_balance",
        "leave_status",
        "cancel_leave",
        "raise_it_ticket",
        "ticket_status",
        "request_asset",
        "asset_status",
        "submit_reimbursement",
        "reimbursement_status",
        "unknown"
    ]

    if intent in allowed_for_all:
        return {
            "allowed": True,
            "message": "Access allowed."
        }

    # HR / Leave approvals
    if intent in ["approve_leave", "reject_leave", "pending_leaves"]:
        if can_approve_leave(role):
            return {
                "allowed": True,
                "message": "Access allowed."
            }

        return {
            "allowed": False,
            "message": "Access denied. Only Manager, HR, or Admin can approve, reject, or view pending leave requests."
        }

    # IT ticket actions
    if intent in ["assign_ticket", "resolve_ticket"]:
        if role in ["it", "admin"]:
            return {
                "allowed": True,
                "message": "Access allowed."
            }

        return {
            "allowed": False,
            "message": "Access denied. Only IT Team or Admin can assign or resolve IT tickets."
        }

    # Manager asset approval
    if intent in ["manager_approve_asset", "manager_reject_asset"]:
        if role in ["manager", "admin"]:
            return {
                "allowed": True,
                "message": "Access allowed."
            }

        return {
            "allowed": False,
            "message": "Access denied. Only Manager or Admin can approve or reject asset requests at manager level."
        }

    # IT asset approval
    if intent in ["it_approve_asset", "it_reject_asset"]:
        if role in ["it", "admin"]:
            return {
                "allowed": True,
                "message": "Access allowed."
            }

        return {
            "allowed": False,
            "message": "Access denied. Only IT Team or Admin can approve or reject asset requests at IT level."
        }

    # Finance approvals
    if intent in ["approve_reimbursement", "reject_reimbursement"]:
        if role in ["finance", "admin"]:
            return {
                "allowed": True,
                "message": "Access allowed."
            }

        return {
            "allowed": False,
            "message": "Access denied. Only Finance Team or Admin can approve or reject reimbursement requests."
        }

    # Pending Approvals
    if intent == "pending_approvals":
        if role in ["manager", "hr", "it", "finance", "admin"]:
            return {
                "allowed": True,
                "message": "Access allowed."
            }
        return {
            "allowed": False,
            "message": "Access denied. Only Manager, HR, IT Team, or Admin can view pending approvals based on their role."
        }

    # Generic Approval (Ambiguous intent)
    if intent == "generic_approval":
        if role in ["manager", "hr", "it", "finance", "admin"]:
            return {
                "allowed": True,
                "message": "Access allowed."
            }
        return {
            "allowed": False,
            "message": "Access denied. Only Manager, HR, IT Team, or Finance can approve requests."
        }

    return {
        "allowed": False,
        "message": "Access denied. This role is not allowed to perform this action."
    }