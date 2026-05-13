from tools.finance_tools import (
    submit_reimbursement,
    get_reimbursement_status,
    approve_reimbursement,
    reject_reimbursement
)

from agents.extraction import (
    extract_claim_type,
    extract_amount,
    extract_request_id
)


def handle_finance_agent(state: dict) -> dict:
    """
    Handles finance-related intents.
    """

    user_input = state["user_input"]
    emp_id = state["emp_id"]
    role = state["role"]
    intent = state["intent"]

    if intent == "submit_reimbursement":
        claim_type = extract_claim_type(user_input)
        amount = extract_amount(user_input)

        missing = []

        if not claim_type:
            missing.append("claim type: travel, internet, food, client meeting, or other")

        if not amount:
            missing.append("amount")

        if missing:
            return {
                "response": (
                    "Please provide the missing reimbursement details: "
                    + ", ".join(missing)
                    + ".\nExample: Submit travel claim of 500 for client meeting."
                ),
                "tool_used": "submit_reimbursement",
                "status": "missing_details"
            }

        result = submit_reimbursement(
            emp_id=emp_id,
            claim_type=claim_type,
            amount=amount,
            description=user_input
        )

        return {
            "response": result["message"],
            "tool_used": "submit_reimbursement",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "reimbursement_status":
        reimbursement_id = extract_request_id(user_input)

        result = get_reimbursement_status(
            emp_id=emp_id,
            role=role,
            reimbursement_id=reimbursement_id
        )

        return {
            "response": result["message"],
            "tool_used": "get_reimbursement_status",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "approve_reimbursement":
        reimbursement_id = extract_request_id(user_input)

        if not reimbursement_id:
            return {
                "response": "Please provide the reimbursement request ID to approve.",
                "tool_used": "approve_reimbursement",
                "status": "missing_details"
            }

        result = approve_reimbursement(
            reimbursement_id=reimbursement_id,
            role=role,
            comment="Approved through Workplace Buddy"
        )

        return {
            "response": result["message"],
            "tool_used": "approve_reimbursement",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "reject_reimbursement":
        reimbursement_id = extract_request_id(user_input)

        if not reimbursement_id:
            return {
                "response": "Please provide the reimbursement request ID to reject.",
                "tool_used": "reject_reimbursement",
                "status": "missing_details"
            }

        result = reject_reimbursement(
            reimbursement_id=reimbursement_id,
            role=role,
            comment="Rejected through Workplace Buddy"
        )

        return {
            "response": result["message"],
            "tool_used": "reject_reimbursement",
            "status": "success" if result["success"] else "failed"
        }

    return {
        "response": "I could not understand the finance request.",
        "tool_used": "finance_agent",
        "status": "unknown"
    }