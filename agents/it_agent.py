from tools.it_tools import (
    create_ticket,
    get_ticket_status,
    assign_ticket,
    resolve_ticket,
    request_asset,
    get_asset_status,
    manager_approve_asset,
    manager_reject_asset,
    it_approve_asset,
    it_reject_asset
)

from agents.extraction import (
    extract_issue_type,
    extract_priority,
    extract_request_id,
    extract_engineer_name,
    extract_asset_type,
    extract_reason
)


def handle_it_agent(state: dict) -> dict:
    """
    Handles IT ticket and asset request intents.
    """

    user_input = state["user_input"]
    emp_id = state["emp_id"]
    role = state["role"]
    intent = state["intent"]

    text = user_input.lower()

    if intent == "raise_it_ticket":
        issue_type = extract_issue_type(user_input)
        priority = extract_priority(user_input)

        if not issue_type:
            return {
                "response": (
                    "Please mention the IT issue type. Allowed types are laptop, VPN, Outlook/email, "
                    "printer, network, or software installation."
                ),
                "tool_used": "create_ticket",
                "status": "missing_details"
            }

        result = create_ticket(
            emp_id=emp_id,
            issue_type=issue_type,
            description=user_input,
            priority=priority
        )

        return {
            "response": result["message"],
            "tool_used": "create_ticket",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "ticket_status":
        wants_all_tickets = "all" in text and "ticket" in text

        if wants_all_tickets and role not in ["it", "admin"]:
            return {
                "response": "Access denied. Only IT Team or Admin can view all IT tickets.",
                "tool_used": "get_ticket_status",
                "status": "denied"
            }

        ticket_id = extract_request_id(user_input)

        result = get_ticket_status(
            emp_id=emp_id,
            role=role,
            ticket_id=ticket_id
        )

        return {
            "response": result["message"],
            "tool_used": "get_ticket_status",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "assign_ticket":
        ticket_id = extract_request_id(user_input)
        engineer_name = extract_engineer_name(user_input)

        if not ticket_id or not engineer_name:
            return {
                "response": "Please provide both ticket ID and engineer name. Example: Assign ticket 1 to Rahul.",
                "tool_used": "assign_ticket",
                "status": "missing_details"
            }

        result = assign_ticket(
            ticket_id=ticket_id,
            engineer_name=engineer_name,
            role=role
        )

        return {
            "response": result["message"],
            "tool_used": "assign_ticket",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "resolve_ticket":
        ticket_id = extract_request_id(user_input)

        if not ticket_id:
            return {
                "response": "Please provide the ticket ID to resolve.",
                "tool_used": "resolve_ticket",
                "status": "missing_details"
            }

        result = resolve_ticket(
            ticket_id=ticket_id,
            role=role
        )

        return {
            "response": result["message"],
            "tool_used": "resolve_ticket",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "request_asset":
        asset_type = extract_asset_type(user_input)
        reason = extract_reason(user_input)

        if not asset_type:
            return {
                "response": (
                    "Please mention the asset type. Allowed assets are laptop, monitor, keyboard, "
                    "mouse, VPN token, and software license."
                ),
                "tool_used": "request_asset",
                "status": "missing_details"
            }

        result = request_asset(
            emp_id=emp_id,
            asset_type=asset_type,
            reason=reason
        )

        return {
            "response": result["message"],
            "tool_used": "request_asset",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "asset_status":
        wants_all_assets = "all" in text and "asset" in text

        if wants_all_assets and role not in ["manager", "it", "admin"]:
            return {
                "response": "Access denied. Only Manager, IT Team, or Admin can view all asset requests.",
                "tool_used": "get_asset_status",
                "status": "denied"
            }

        request_id = extract_request_id(user_input)

        result = get_asset_status(
            emp_id=emp_id,
            role=role,
            request_id=request_id
        )

        return {
            "response": result["message"],
            "tool_used": "get_asset_status",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "manager_approve_asset":
        request_id = extract_request_id(user_input)

        if not request_id:
            return {
                "response": "Please provide the asset request ID for manager approval.",
                "tool_used": "manager_approve_asset",
                "status": "missing_details"
            }

        result = manager_approve_asset(
            request_id=request_id,
            role=role
        )

        return {
            "response": result["message"],
            "tool_used": "manager_approve_asset",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "manager_reject_asset":
        request_id = extract_request_id(user_input)

        if not request_id:
            return {
                "response": "Please provide the asset request ID for manager rejection.",
                "tool_used": "manager_reject_asset",
                "status": "missing_details"
            }

        result = manager_reject_asset(
            request_id=request_id,
            role=role
        )

        return {
            "response": result["message"],
            "tool_used": "manager_reject_asset",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "it_approve_asset":
        request_id = extract_request_id(user_input)

        if not request_id:
            return {
                "response": "Please provide the asset request ID for IT approval.",
                "tool_used": "it_approve_asset",
                "status": "missing_details"
            }

        result = it_approve_asset(
            request_id=request_id,
            role=role
        )

        return {
            "response": result["message"],
            "tool_used": "it_approve_asset",
            "status": "success" if result["success"] else "failed"
        }

    if intent == "it_reject_asset":
        request_id = extract_request_id(user_input)

        if not request_id:
            return {
                "response": "Please provide the asset request ID for IT rejection.",
                "tool_used": "it_reject_asset",
                "status": "missing_details"
            }

        result = it_reject_asset(
            request_id=request_id,
            role=role
        )

        return {
            "response": result["message"],
            "tool_used": "it_reject_asset",
            "status": "success" if result["success"] else "failed"
        }

    return {
        "response": "I could not understand the IT request.",
        "tool_used": "it_agent",
        "status": "unknown"
    }