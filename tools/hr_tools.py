from datetime import datetime
from database.db import get_connection
from tools.email_tools import send_email


def get_user(emp_id: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT emp_id, name, email, role, department
    FROM users
    WHERE emp_id = ?
    """, (emp_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def calculate_leave_days(start_date: str, end_date: str) -> int:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    return (end - start).days + 1


def validate_dates(start_date: str, end_date: str) -> tuple[bool, str]:
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        if end < start:
            return False, "End date cannot be before start date."

        return True, "Valid dates."

    except ValueError:
        return False, "Invalid date format. Please use YYYY-MM-DD."


def check_overlapping_leave(emp_id: str, start_date: str, end_date: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id
    FROM leave_requests
    WHERE emp_id = ?
    AND status IN ('pending', 'approved')
    AND NOT (end_date < ? OR start_date > ?)
    """, (emp_id, start_date, end_date))

    row = cursor.fetchone()
    conn.close()

    return row is not None


def get_leave_balance(emp_id: str) -> dict:
    user = get_user(emp_id)

    if not user:
        return {
            "success": False,
            "message": "Employee not found."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM leave_balances
    WHERE emp_id = ?
    """, (emp_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "success": False,
            "message": "Leave balance not found."
        }

    data = dict(row)

    return {
        "success": True,
        "message": (
            f"Leave balance for {user['name']} ({emp_id}):\n"
            f"Casual Leave: Total {data['casual_total']}, Used {data['casual_used']}, Remaining {data['casual_total'] - data['casual_used']}\n"
            f"Sick Leave: Total {data['sick_total']}, Used {data['sick_used']}, Remaining {data['sick_total'] - data['sick_used']}\n"
            f"Earned Leave: Total {data['earned_total']}, Used {data['earned_used']}, Remaining {data['earned_total'] - data['earned_used']}"
        ),
        "data": data
    }


def apply_leave(
    emp_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str
) -> dict:
    user = get_user(emp_id)

    if not user:
        return {
            "success": False,
            "message": "Employee not found."
        }

    leave_type = leave_type.lower().strip()

    if leave_type not in ["casual", "sick", "earned"]:
        return {
            "success": False,
            "message": "Invalid leave type. Allowed types are casual, sick, and earned."
        }

    valid, validation_message = validate_dates(start_date, end_date)

    if not valid:
        return {
            "success": False,
            "message": validation_message
        }

    if check_overlapping_leave(emp_id, start_date, end_date):
        return {
            "success": False,
            "message": "You already have a pending or approved leave request for these dates."
        }

    days = calculate_leave_days(start_date, end_date)

    balance_result = get_leave_balance(emp_id)

    if not balance_result["success"]:
        return balance_result

    balance = balance_result["data"]

    total_key = f"{leave_type}_total"
    used_key = f"{leave_type}_used"

    remaining = balance[total_key] - balance[used_key]

    if days > remaining:
        return {
            "success": False,
            "message": f"Insufficient {leave_type} leave balance. Required: {days}, Available: {remaining}."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO leave_requests (
        emp_id,
        leave_type,
        start_date,
        end_date,
        reason,
        status
    )
    VALUES (?, ?, ?, ?, ?, 'pending')
    """, (emp_id, leave_type, start_date, end_date, reason))

    request_id = cursor.lastrowid

    conn.commit()
    conn.close()

    send_email(
        to="manager@company.com",
        subject=f"Leave Approval Request - {user['name']}",
        body=(
            f"{user['name']} ({emp_id}) has requested {leave_type} leave "
            f"from {start_date} to {end_date} for {days} day(s).\n\n"
            f"Reason: {reason}\n"
            f"Request ID: {request_id}"
        )
    )

    return {
        "success": True,
        "message": (
            f"Leave request submitted successfully.\n"
            f"Request ID: {request_id}\n"
            f"Employee: {user['name']} ({emp_id})\n"
            f"Leave Type: {leave_type}\n"
            f"Dates: {start_date} to {end_date}\n"
            f"Days: {days}\n"
            f"Status: Pending manager approval."
        ),
        "request_id": request_id
    }


def get_leave_status(emp_id: str) -> dict:
    user = get_user(emp_id)

    if not user:
        return {
            "success": False,
            "message": "Employee not found."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM leave_requests
    WHERE emp_id = ?
    ORDER BY created_at DESC
    LIMIT 5
    """, (emp_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "success": True,
            "message": "No leave requests found.",
            "data": []
        }

    lines = [f"Recent leave requests for {user['name']} ({emp_id}):"]

    for row in rows:
        item = dict(row)
        lines.append(
            f"ID {item['id']} | {item['leave_type']} | "
            f"{item['start_date']} to {item['end_date']} | Status: {item['status']}"
        )

    return {
        "success": True,
        "message": "\n".join(lines),
        "data": [dict(row) for row in rows]
    }


def cancel_leave(emp_id: str, request_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM leave_requests
    WHERE id = ? AND emp_id = ?
    """, (request_id, emp_id))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "message": "Leave request not found for this employee."
        }

    leave = dict(row)

    if leave["status"] != "pending":
        conn.close()
        return {
            "success": False,
            "message": "Only pending leave requests can be cancelled."
        }

    cursor.execute("""
    UPDATE leave_requests
    SET status = 'cancelled',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (request_id,))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Leave request {request_id} cancelled successfully."
    }


def approve_leave(request_id: int, approver_role: str, comment: str = "") -> dict:
    approver_role = approver_role.lower().strip()

    if approver_role not in ["manager", "hr", "admin"]:
        return {
            "success": False,
            "message": "Only Manager, HR, or Admin can approve leave requests."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM leave_requests
    WHERE id = ?
    """, (request_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "message": "Leave request not found."
        }

    leave = dict(row)

    if leave["status"] != "pending":
        conn.close()
        return {
            "success": False,
            "message": "Only pending leave requests can be approved."
        }

    days = calculate_leave_days(leave["start_date"], leave["end_date"])
    used_column = f"{leave['leave_type']}_used"

    cursor.execute(f"""
    UPDATE leave_balances
    SET {used_column} = {used_column} + ?
    WHERE emp_id = ?
    """, (days, leave["emp_id"]))

    cursor.execute("""
    UPDATE leave_requests
    SET status = 'approved',
        manager_comment = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (comment, request_id))

    cursor.execute("""
    SELECT name, email
    FROM users
    WHERE emp_id = ?
    """, (leave["emp_id"],))

    user = cursor.fetchone()

    conn.commit()
    conn.close()

    if user:
        send_email(
            to=user["email"],
            subject="Leave Request Approved",
            body=f"Your leave request ID {request_id} has been approved."
        )

    return {
        "success": True,
        "message": f"Leave request {request_id} approved successfully."
    }


def reject_leave(request_id: int, approver_role: str, comment: str = "") -> dict:
    approver_role = approver_role.lower().strip()

    if approver_role not in ["manager", "hr", "admin"]:
        return {
            "success": False,
            "message": "Only Manager, HR, or Admin can reject leave requests."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM leave_requests
    WHERE id = ?
    """, (request_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "message": "Leave request not found."
        }

    leave = dict(row)

    if leave["status"] != "pending":
        conn.close()
        return {
            "success": False,
            "message": "Only pending leave requests can be rejected."
        }

    cursor.execute("""
    UPDATE leave_requests
    SET status = 'rejected',
        manager_comment = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (comment, request_id))

    cursor.execute("""
    SELECT email
    FROM users
    WHERE emp_id = ?
    """, (leave["emp_id"],))

    user = cursor.fetchone()

    conn.commit()
    conn.close()

    if user:
        send_email(
            to=user["email"],
            subject="Leave Request Rejected",
            body=f"Your leave request ID {request_id} has been rejected. Comment: {comment}"
        )

    return {
        "success": True,
        "message": f"Leave request {request_id} rejected successfully."
    }


def get_pending_leaves(role: str) -> dict:
    role = role.lower().strip()

    if role not in ["manager", "hr", "admin"]:
        return {
            "success": False,
            "message": "Only Manager, HR, or Admin can view pending leave requests."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT leave_requests.*, users.name
    FROM leave_requests
    JOIN users ON leave_requests.emp_id = users.emp_id
    WHERE leave_requests.status = 'pending'
    ORDER BY leave_requests.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "success": True,
            "message": "No pending leave requests.",
            "data": []
        }

    lines = ["Pending leave requests:"]

    for row in rows:
        item = dict(row)
        lines.append(
            f"ID {item['id']} | {item['name']} ({item['emp_id']}) | "
            f"{item['leave_type']} | {item['start_date']} to {item['end_date']} | "
            f"Reason: {item['reason']}"
        )

    return {
        "success": True,
        "message": "\n".join(lines),
        "data": [dict(row) for row in rows]
    }