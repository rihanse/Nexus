from tools.hr_tools import (
    apply_leave,
    get_leave_balance,
    get_leave_status,
    get_pending_leaves,
    approve_leave,
    reject_leave,
    cancel_leave
)

from agents.extraction import (
    extract_dates,
    extract_leave_type,
    extract_reason,
    extract_request_id
)


def handle_hr_agent(state: dict) -> dict:
    """
    Handles HR-related intents.
    """

    user_input = state["user_input"]
    emp_id = state["emp_id"]
    role = state["role"]
    intent = state["intent"]

    if intent == "leave_balance":
        result = get_leave_balance(emp_id)

        return {
            "response": result["message"],
            "tool_used": "get_leave_balance",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "leave_status":
        result = get_leave_status(emp_id)

        return {
            "response": result["message"],
            "tool_used": "get_leave_status",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "pending_leaves":
        result = get_pending_leaves(role)

        return {
            "response": result["message"],
            "tool_used": "get_pending_leaves",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "apply_leave":
        leave_type = extract_leave_type(user_input) or "casual"
        start_date, end_date = extract_dates(user_input)
        reason = extract_reason(user_input) or "Personal reason"

        missing = []

        if not start_date:
            missing.append("date in YYYY-MM-DD format")

        if missing:
            return {
                "response": (
                    "Please provide the missing leave details: "
                    + ", ".join(missing)
                    + ".\nExample: I want to apply casual leave on 2026-06-10 because family function."
                ),
                "tool_used": "apply_leave",
                "status": "missing_details"
            }

        result = apply_leave(
            emp_id=emp_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )

        return {
            "response": result["message"],
            "tool_used": "apply_leave",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "approve_leave":
        request_id = extract_request_id(user_input)

        if not request_id:
            return {
                "response": "Please provide the leave request ID to approve.",
                "tool_used": "approve_leave",
                "status": "missing_details"
            }

        result = approve_leave(
            request_id=request_id,
            approver_role=role,
            comment="Approved through Workplace Buddy"
        )

        return {
            "response": result["message"],
            "tool_used": "approve_leave",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "reject_leave":
        request_id = extract_request_id(user_input)

        if not request_id:
            return {
                "response": "Please provide the leave request ID to reject.",
                "tool_used": "reject_leave",
                "status": "missing_details"
            }

        result = reject_leave(
            request_id=request_id,
            approver_role=role,
            comment="Rejected through Workplace Buddy"
        )

        return {
            "response": result["message"],
            "tool_used": "reject_leave",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "cancel_leave":
        request_id = extract_request_id(user_input)

        if not request_id:
            return {
                "response": "Please provide the leave request ID to cancel.",
                "tool_used": "cancel_leave",
                "status": "missing_details"
            }

        result = cancel_leave(
            emp_id=emp_id,
            request_id=request_id
        )

        return {
            "response": result["message"],
            "tool_used": "cancel_leave",
            "status": "success" if result["success"] else "failed"
        }

    return {
        "response": "I could not understand the HR request.",
        "tool_used": "hr_agent",
        "status": "unknown"
    }