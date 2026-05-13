from database.db import get_connection
from tools.hr_tools import get_user
from tools.email_tools import send_email


def check_known_outage(issue_type: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM known_outages
    WHERE lower(issue_type) = lower(?)
    AND status = 'active'
    ORDER BY created_at DESC
    LIMIT 1
    """, (issue_type,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def check_maintenance(issue_type: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM maintenance_schedule
    WHERE lower(system_name) = lower(?)
    AND status = 'scheduled'
    ORDER BY maintenance_date ASC
    LIMIT 1
    """, (issue_type,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def check_duplicate_ticket(emp_id: str, issue_type: str) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM it_tickets
    WHERE emp_id = ?
    AND lower(issue_type) = lower(?)
    AND status IN ('open', 'in_progress')
    ORDER BY created_at DESC
    LIMIT 1
    """, (emp_id, issue_type))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def create_ticket(
    emp_id: str,
    issue_type: str,
    description: str,
    priority: str = "medium"
) -> dict:
    user = get_user(emp_id)

    if not user:
        return {
            "success": False,
            "message": "Employee not found."
        }

    issue_type = issue_type.lower().strip()
    priority = priority.lower().strip()

    allowed_issues = [
        "laptop",
        "vpn",
        "outlook",
        "email",
        "printer",
        "network",
        "software installation",
        "software"
    ]

    if issue_type not in allowed_issues:
        return {
            "success": False,
            "message": (
                "Invalid issue type. Allowed types are laptop, vpn, outlook, email, "
                "printer, network, and software installation."
            )
        }

    outage = check_known_outage(issue_type)

    if outage:
        return {
            "success": True,
            "message": (
                f"This issue is already known: {outage['description']}\n"
                f"No new ticket was created to avoid duplicates."
            ),
            "known_outage": outage
        }

    maintenance = check_maintenance(issue_type)

    if maintenance:
        return {
            "success": True,
            "message": (
                f"There is planned maintenance for {issue_type}: {maintenance['description']}\n"
                f"Maintenance Date: {maintenance['maintenance_date']}\n"
                f"No new ticket was created."
            ),
            "maintenance": maintenance
        }

    duplicate = check_duplicate_ticket(emp_id, issue_type)

    if duplicate:
        return {
            "success": True,
            "message": (
                f"You already have an open ticket for {issue_type}.\n"
                f"Ticket ID: {duplicate['id']}\n"
                f"Status: {duplicate['status']}"
            ),
            "duplicate_ticket": duplicate
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO it_tickets (
        emp_id,
        issue_type,
        description,
        priority,
        status
    )
    VALUES (?, ?, ?, ?, 'open')
    """, (emp_id, issue_type, description, priority))

    ticket_id = cursor.lastrowid

    conn.commit()
    conn.close()

    send_email(
        to=user["email"],
        subject="IT Ticket Created",
        body=(
            f"Your IT ticket has been created.\n"
            f"Ticket ID: {ticket_id}\n"
            f"Issue Type: {issue_type}\n"
            f"Priority: {priority}\n"
            f"Status: Open"
        )
    )

    return {
        "success": True,
        "message": (
            f"IT ticket created successfully.\n"
            f"Ticket ID: {ticket_id}\n"
            f"Employee: {user['name']} ({emp_id})\n"
            f"Issue Type: {issue_type}\n"
            f"Priority: {priority}\n"
            f"Status: Open"
        ),
        "ticket_id": ticket_id
    }


def get_ticket_status(emp_id: str, role: str, ticket_id: int | None = None) -> dict:
    user = get_user(emp_id)

    if not user:
        return {
            "success": False,
            "message": "Employee not found."
        }

    role = role.lower().strip()

    conn = get_connection()
    cursor = conn.cursor()

    if ticket_id:
        if role in ["it", "admin"]:
            cursor.execute("""
            SELECT it_tickets.*, users.name
            FROM it_tickets
            JOIN users ON it_tickets.emp_id = users.emp_id
            WHERE it_tickets.id = ?
            """, (ticket_id,))
        else:
            cursor.execute("""
            SELECT it_tickets.*, users.name
            FROM it_tickets
            JOIN users ON it_tickets.emp_id = users.emp_id
            WHERE it_tickets.id = ?
            AND it_tickets.emp_id = ?
            """, (ticket_id, emp_id))
    else:
        if role in ["it", "admin"]:
            cursor.execute("""
            SELECT it_tickets.*, users.name
            FROM it_tickets
            JOIN users ON it_tickets.emp_id = users.emp_id
            ORDER BY it_tickets.created_at DESC
            LIMIT 10
            """)
        else:
            cursor.execute("""
            SELECT it_tickets.*, users.name
            FROM it_tickets
            JOIN users ON it_tickets.emp_id = users.emp_id
            WHERE it_tickets.emp_id = ?
            ORDER BY it_tickets.created_at DESC
            LIMIT 10
            """, (emp_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "success": True,
            "message": "No IT tickets found.",
            "data": []
        }

    lines = ["IT ticket status:"]

    for row in rows:
        item = dict(row)
        lines.append(
            f"Ticket {item['id']} | {item['name']} ({item['emp_id']}) | "
            f"{item['issue_type']} | Priority: {item['priority']} | "
            f"Status: {item['status']} | Engineer: {item['assigned_engineer'] or 'Not assigned'}"
        )

    return {
        "success": True,
        "message": "\n".join(lines),
        "data": [dict(row) for row in rows]
    }


def assign_ticket(ticket_id: int, engineer_name: str, role: str) -> dict:
    role = role.lower().strip()

    if role not in ["it", "admin"]:
        return {
            "success": False,
            "message": "Only IT Team or Admin can assign tickets."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM it_tickets
    WHERE id = ?
    """, (ticket_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "message": "Ticket not found."
        }

    cursor.execute("""
    UPDATE it_tickets
    SET assigned_engineer = ?,
        status = 'in_progress',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (engineer_name, ticket_id))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": f"Ticket {ticket_id} assigned to {engineer_name}."
    }


def resolve_ticket(ticket_id: int, role: str) -> dict:
    role = role.lower().strip()

    if role not in ["it", "admin"]:
        return {
            "success": False,
            "message": "Only IT Team or Admin can resolve tickets."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT it_tickets.*, users.email
    FROM it_tickets
    JOIN users ON it_tickets.emp_id = users.emp_id
    WHERE it_tickets.id = ?
    """, (ticket_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "message": "Ticket not found."
        }

    ticket = dict(row)

    if ticket["status"] == "resolved":
        conn.close()
        return {
            "success": False,
            "message": "Ticket is already resolved."
        }

    cursor.execute("""
    UPDATE it_tickets
    SET status = 'resolved',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (ticket_id,))

    conn.commit()
    conn.close()

    send_email(
        to=ticket["email"],
        subject="IT Ticket Resolved",
        body=f"Your IT ticket ID {ticket_id} has been resolved."
    )

    return {
        "success": True,
        "message": f"Ticket {ticket_id} resolved successfully."
    }


def request_asset(emp_id: str, asset_type: str, reason: str) -> dict:
    user = get_user(emp_id)

    if not user:
        return {
            "success": False,
            "message": "Employee not found."
        }

    asset_type = asset_type.lower().strip()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id
    FROM asset_requests
    WHERE emp_id = ?
    AND status NOT IN ('fulfilled', 'rejected')
    LIMIT 1
    """, (emp_id,))

    active_request = cursor.fetchone()

    if active_request:
        conn.close()
        return {
            "success": False,
            "message": (
                f"You already have an active asset request. "
                f"Request ID: {active_request['id']}"
            )
        }

    cursor.execute("""
    SELECT *
    FROM inventory
    WHERE lower(asset_type) = lower(?)
    """, (asset_type,))

    inventory = cursor.fetchone()

    if not inventory:
        conn.close()
        return {
            "success": False,
            "message": "Asset type not found in inventory."
        }

    cursor.execute("""
    INSERT INTO asset_requests (
        emp_id,
        asset_type,
        reason,
        status
    )
    VALUES (?, ?, ?, 'pending_manager_approval')
    """, (emp_id, asset_type, reason))

    request_id = cursor.lastrowid

    conn.commit()
    conn.close()

    send_email(
        to="manager@company.com",
        subject=f"Asset Approval Request - {user['name']}",
        body=(
            f"{user['name']} ({emp_id}) requested asset: {asset_type}\n"
            f"Reason: {reason}\n"
            f"Request ID: {request_id}"
        )
    )

    return {
        "success": True,
        "message": (
            f"Asset request submitted successfully.\n"
            f"Request ID: {request_id}\n"
            f"Asset: {asset_type}\n"
            f"Status: Pending manager approval."
        ),
        "request_id": request_id
    }


def manager_approve_asset(request_id: int, role: str) -> dict:
    role = role.lower().strip()

    if role not in ["manager", "admin"]:
        return {
            "success": False,
            "message": "Only Manager or Admin can approve asset requests at manager level."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM asset_requests
    WHERE id = ?
    """, (request_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "message": "Asset request not found."
        }

    request_data = dict(row)

    if request_data["manager_approval"] != "pending":
        conn.close()
        return {
            "success": False,
            "message": "Manager approval is already completed for this request."
        }

    cursor.execute("""
    UPDATE asset_requests
    SET manager_approval = 'approved',
        status = 'pending_it_approval',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (request_id,))

    conn.commit()
    conn.close()

    send_email(
        to="it@company.com",
        subject="Asset Request Pending IT Approval",
        body=f"Asset request ID {request_id} is approved by manager and waiting for IT approval."
    )

    return {
        "success": True,
        "message": f"Asset request {request_id} approved by manager. Waiting for IT approval."
    }


def manager_reject_asset(request_id: int, role: str) -> dict:
    role = role.lower().strip()

    if role not in ["manager", "admin"]:
        return {
            "success": False,
            "message": "Only Manager or Admin can reject asset requests at manager level."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE asset_requests
    SET manager_approval = 'rejected',
        status = 'rejected',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    AND manager_approval = 'pending'
    """, (request_id,))

    updated = cursor.rowcount

    conn.commit()
    conn.close()

    if updated == 0:
        return {
            "success": False,
            "message": "Asset request not found or already processed."
        }

    return {
        "success": True,
        "message": f"Asset request {request_id} rejected by manager."
    }


def it_approve_asset(request_id: int, role: str) -> dict:
    role = role.lower().strip()

    if role not in ["it", "admin"]:
        return {
            "success": False,
            "message": "Only IT Team or Admin can approve asset requests at IT level."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM asset_requests
    WHERE id = ?
    """, (request_id,))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "message": "Asset request not found."
        }

    request_data = dict(row)

    if request_data["manager_approval"] != "approved":
        conn.close()
        return {
            "success": False,
            "message": "Manager approval is required before IT approval."
        }

    cursor.execute("""
    SELECT *
    FROM inventory
    WHERE lower(asset_type) = lower(?)
    """, (request_data["asset_type"],))

    inventory = cursor.fetchone()

    if not inventory or inventory["available_quantity"] <= 0:
        cursor.execute("""
        UPDATE asset_requests
        SET it_approval = 'approved',
            inventory_status = 'out_of_stock',
            status = 'waiting_for_inventory',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (request_id,))

        conn.commit()
        conn.close()

        return {
            "success": False,
            "message": "IT approved, but asset is currently out of stock."
        }

    cursor.execute("""
    UPDATE inventory
    SET available_quantity = available_quantity - 1
    WHERE lower(asset_type) = lower(?)
    """, (request_data["asset_type"],))

    cursor.execute("""
    UPDATE asset_requests
    SET it_approval = 'approved',
        inventory_status = 'available',
        status = 'fulfilled',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (request_id,))

    cursor.execute("""
    SELECT users.email
    FROM users
    JOIN asset_requests ON users.emp_id = asset_requests.emp_id
    WHERE asset_requests.id = ?
    """, (request_id,))

    user = cursor.fetchone()

    conn.commit()
    conn.close()

    if user:
        send_email(
            to=user["email"],
            subject="Asset Request Fulfilled",
            body=f"Your asset request ID {request_id} has been approved and fulfilled."
        )

    return {
        "success": True,
        "message": f"Asset request {request_id} approved by IT and fulfilled."
    }


def it_reject_asset(request_id: int, role: str) -> dict:
    role = role.lower().strip()

    if role not in ["it", "admin"]:
        return {
            "success": False,
            "message": "Only IT Team or Admin can reject asset requests at IT level."
        }

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE asset_requests
    SET it_approval = 'rejected',
        status = 'rejected',
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (request_id,))

    updated = cursor.rowcount

    conn.commit()
    conn.close()

    if updated == 0:
        return {
            "success": False,
            "message": "Asset request not found."
        }

    return {
        "success": True,
        "message": f"Asset request {request_id} rejected by IT."
    }


def get_asset_status(emp_id: str, role: str, request_id: int | None = None) -> dict:
    role = role.lower().strip()

    conn = get_connection()
    cursor = conn.cursor()

    if request_id:
        if role in ["manager", "it", "admin"]:
            cursor.execute("""
            SELECT asset_requests.*, users.name
            FROM asset_requests
            JOIN users ON asset_requests.emp_id = users.emp_id
            WHERE asset_requests.id = ?
            """, (request_id,))
        else:
            cursor.execute("""
            SELECT asset_requests.*, users.name
            FROM asset_requests
            JOIN users ON asset_requests.emp_id = users.emp_id
            WHERE asset_requests.id = ?
            AND asset_requests.emp_id = ?
            """, (request_id, emp_id))
    else:
        if role in ["manager", "it", "admin"]:
            cursor.execute("""
            SELECT asset_requests.*, users.name
            FROM asset_requests
            JOIN users ON asset_requests.emp_id = users.emp_id
            ORDER BY asset_requests.created_at DESC
            LIMIT 10
            """)
        else:
            cursor.execute("""
            SELECT asset_requests.*, users.name
            FROM asset_requests
            JOIN users ON asset_requests.emp_id = users.emp_id
            WHERE asset_requests.emp_id = ?
            ORDER BY asset_requests.created_at DESC
            LIMIT 10
            """, (emp_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return {
            "success": True,
            "message": "No asset requests found.",
            "data": []
        }

    lines = ["Asset request status:"]

    for row in rows:
        item = dict(row)
        lines.append(
            f"Request {item['id']} | {item['name']} ({item['emp_id']}) | "
            f"{item['asset_type']} | Manager: {item['manager_approval']} | "
            f"IT: {item['it_approval']} | Inventory: {item['inventory_status']} | "
            f"Status: {item['status']}"
        )

    return {
        "success": True,
        "message": "\n".join(lines),
        "data": [dict(row) for row in rows]
    }