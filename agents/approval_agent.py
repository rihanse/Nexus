from database.db import get_connection

def handle_approval_agent(state: dict) -> dict:
    role = state.get("role", "employee").lower()
    
    if role == "employee":
        return {
            "response": "Access denied. Only Manager, HR, IT Team, or Admin can view pending approvals based on their role.",
            "tool_used": "rbac_validator",
            "status": "denied"
        }

    conn = get_connection()
    cursor = conn.cursor()
    
    response_lines = ["Pending Approvals\n"]
    
    # Leave Requests
    if role in ["manager", "hr", "admin"]:
        cursor.execute("SELECT id, emp_id, leave_type, start_date, end_date FROM leave_requests WHERE status = 'pending'")
        leaves = cursor.fetchall()
        response_lines.append("Leave Requests:")
        if leaves:
            for l in leaves:
                response_lines.append(f"- Request {l['id']}: {l['emp_id']} ({l['leave_type']}, {l['start_date']} to {l['end_date']})")
        else:
            response_lines.append("- list pending leave approvals if any")
        response_lines.append("")
        
    # Asset Requests
    if role in ["manager", "it", "admin"]:
        # Pending Manager Approval (for manager/admin)
        if role in ["manager", "admin"]:
            cursor.execute("SELECT id, emp_id, asset_type, reason, status FROM asset_requests WHERE manager_approval = 'pending' AND status != 'rejected'")
            manager_assets = cursor.fetchall()
            
            response_lines.append("Asset Requests Pending Manager Approval:")
            if manager_assets:
                for a in manager_assets:
                    reason = a["reason"] or "N/A"
                    status = a["status"] or "Pending manager approval"
                    response_lines.append(f"- Request ID: {a['id']} | Employee: {a['emp_id']} | Asset: {a['asset_type']} | Reason: {reason} | Status: {status}")
            else:
                response_lines.append("No asset requests are currently pending manager approval.")
            response_lines.append("")
            
        # Pending IT Approval (for it/admin)
        if role in ["it", "admin"]:
            cursor.execute("SELECT id, emp_id, asset_type, status FROM asset_requests WHERE manager_approval = 'approved' AND it_approval = 'pending'")
            it_assets = cursor.fetchall()
            
            response_lines.append("Asset Requests Pending IT Approval:")
            if it_assets:
                for a in it_assets:
                    status = a["status"] or "Pending IT approval"
                    response_lines.append(f"- Request ID: {a['id']} | Employee: {a['emp_id']} | Asset: {a['asset_type']} | Status: {status}")
            else:
                response_lines.append("No asset requests are currently pending IT approval.")
            response_lines.append("")
            
            # For IT, also show requests waiting for manager approval (informational only)
            if role == "it":
                cursor.execute("SELECT id, emp_id, asset_type, status FROM asset_requests WHERE manager_approval = 'pending' AND status != 'rejected'")
                waiting_manager_assets = cursor.fetchall()
                if waiting_manager_assets:
                    response_lines.append("Asset Requests Waiting for Manager Approval:")
                    for a in waiting_manager_assets:
                        status = a["status"] or "Pending manager approval"
                        response_lines.append(f"- Request ID: {a['id']} | Employee: {a['emp_id']} | Asset: {a['asset_type']} | Status: {status}")
                    response_lines.append("")

    # Finance Requests
    if role in ["finance", "admin"]:
        try:
            cursor.execute("SELECT id, emp_id, claim_type, amount FROM reimbursements WHERE status = 'pending'")
            reimbursements = cursor.fetchall()
            response_lines.append("Finance Requests:")
            if reimbursements:
                for r in reimbursements:
                    response_lines.append(f"- Request {r['id']}: {r['emp_id']} ({r['claim_type']}, ${r['amount']})")
            else:
                response_lines.append("- list pending reimbursements if implemented")
        except Exception:
            pass # Table might not exist yet if finance isn't implemented

    conn.close()

    if state.get("intent") == "generic_approval":
        request_id = state.get("request_id")
        if request_id:
            return {
                "response": f"Do you want to approve leave request {request_id}, asset request {request_id}, or finance request {request_id}?",
                "tool_used": "generic_approval",
                "status": "clarification_needed"
            }
        else:
            return {
                "response": "Could you please clarify which request or ticket you want to approve?",
                "tool_used": "generic_approval",
                "status": "clarification_needed"
            }

    return {
        "response": "\n".join(response_lines).strip(),
        "tool_used": "get_pending_approvals",
        "status": "success"
    }
