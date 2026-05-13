from database.db import get_connection
from tools.hr_tools import get_user
from tools.email_tools import send_email


def submit_reimbursement(
    emp_id: str,
    claim_type: str,
    amount: float,
    description: str
) -> dict:
    user = get_user(emp_id)

    if not user:
        return {
            "success": False,
            "message": "Employee not found."
        }

    claim_type = claim_type.lower().strip()

    allowed_claims = [
        "travel",
        "internet",
        "food",
        "client meeting",
        "other"
    ]

    if claim_type not in allowed_claims:
        return {
            "success": False,
            "message": "Invalid claim type. Allowed types are travel, internet, food, client meeting, and other."
        }

    if amount <= 0:
        return {
            "success": False,
            "message": "Amount must be greater than zero."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reimbursements (
        emp_id,
        claim_type,
        amount,
        description,
        status
    )
    VALUES (?, ?, ?, ?, 'pending')
    """, (emp_id, claim_type, amount, description))

    reimbursement_id = cursor.lastrowid

    conn.commit()
    conn.close()

    send_email(
        to="finance@company.com",
        subject=f"Reimbursement Approval Request - {user['name']}",
        body=(
            f"{user['name']} ({emp_id}) submitted a reimbursement request.\n"
            f"Claim Type: {claim_type}\n"
            f"Amount: {amount}\n"
            f"Description: {description}\n"
            f"Request ID: {reimbursement_id}"
        )
    )

    return {
        "success": True,
        "message": (
            f"Reimbursement request submitted successfully.\n"
            f"Request ID: {reimbursement_id}\n"
            f"Claim Type: {claim_type}\n"
            f"Amount: {amount}\n"
            f"Status: Pending finance approval."
        ),
        "reimbursement_id": reimbursement_id
    }


def get_reimbursement_status(
    emp_id: str,
    role: str,
    reimbursement_id: int | None = None
) -> dict:
    role = role.lower().strip()

    conn = get_connection()
    cursor = conn.cursor()

    if reimbursement_id:
        if role in ["finance", "admin"]:
            cursor.execute("""
            SELECT reimbursements.*, users.name
            FROM reimbursements
            JOIN users ON reimbursements.emp_id = users.emp_id
            WHERE reimbursements.id = ?
            """, (reimbursement_id,))
        else:
            cursor.execute("""
            SELECT reimbursements.*, users.name
            FROM reimbursements
            JOIN users ON reimbursements.emp_id = users.emp_id
            WHERE reimbursements.id = ?
            AND reimbursements.emp_id = ?
            """, (reimbursement_id, emp_id))
    else:
        if role in ["finance", "admin"]:
            cursor.execute("""
            SELECT reimbursements.*, users.name
            FROM reimbursements
            JOIN users ON reimbursements.emp_id = users.emp_id
            ORDER BY reimbursements.created_at DESC
            LIMIT 10
            """)
        else:
            cursor.execute("""
            SELECT reimbursements.*, users.name
            FROM reimbursements
            JOIN users ON reimbursements.emp_id = users.emp_id
            WHERE reimbursements.emp_id = ?
            ORDER BY reimbursements.created_at DESC
            LIMIT 10
            """, (emp_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "success": True,
            "message": "No reimbursement requests found.",
            "data": []
        }

    lines = ["Reimbursement status:"]

    for row in rows:
        item = dict(row)
        lines.append(
            f"Request {item['id']} | {item['name']} ({item['emp_id']}) | "
            f"{item['claim_type']} | Amount: {item['amount']} | Status: {item['status']}"
        )

    return {
        "success": True,
        "message": "\n".join(lines),
        "data": [dict(row) for row in rows]
    }


def approve_reimbursement(
    reimbursement_id: int,
    role: str,
    comment: str = ""
) -> dict:
    role = role.lower().strip()

    if role not in ["finance", "admin"]:
        return {
            "success": False,
            "message": "Only Finance Team or Admin can approve reimbursement requests."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT reimbursements.*, users.email
    FROM reimbursements
    JOIN users ON reimbursements.emp_id = users.emp_id
    WHERE reimbursements.id = ?
    """, (reimbursement_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "message": "Reimbursement request not found."
        }

    reimbursement = dict(row)

    if reimbursement["status"] != "pending":
        conn.close()
        return {
            "success": False,
            "message": "Only pending reimbursement requests can be approved."
        }

    cursor.execute("""
    UPDATE reimbursements
    SET status = 'approved',
        finance_comment = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (comment, reimbursement_id))

    conn.commit()
    conn.close()

    send_email(
        to=reimbursement["email"],
        subject="Reimbursement Approved",
        body=f"Your reimbursement request ID {reimbursement_id} has been approved."
    )

    return {
        "success": True,
        "message": f"Reimbursement request {reimbursement_id} approved successfully."
    }


def reject_reimbursement(
    reimbursement_id: int,
    role: str,
    comment: str = ""
) -> dict:
    role = role.lower().strip()

    if role not in ["finance", "admin"]:
        return {
            "success": False,
            "message": "Only Finance Team or Admin can reject reimbursement requests."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT reimbursements.*, users.email
    FROM reimbursements
    JOIN users ON reimbursements.emp_id = users.emp_id
    WHERE reimbursements.id = ?
    """, (reimbursement_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "message": "Reimbursement request not found."
        }

    reimbursement = dict(row)

    if reimbursement["status"] != "pending":
        conn.close()
        return {
            "success": False,
            "message": "Only pending reimbursement requests can be rejected."
        }

    cursor.execute("""
    UPDATE reimbursements
    SET status = 'rejected',
        finance_comment = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (comment, reimbursement_id))

    conn.commit()
    conn.close()

    send_email(
        to=reimbursement["email"],
        subject="Reimbursement Rejected",
        body=f"Your reimbursement request ID {reimbursement_id} has been rejected. Comment: {comment}"
    )

    return {
        "success": True,
        "message": f"Reimbursement request {reimbursement_id} rejected successfully."
    }