from database.db import get_connection
from database.schema import create_tables


def seed_users(cursor):
    users = [
        ("EMP001", "Rifa", "rifa@company.com", "employee", "Engineering"),
        ("EMP002", "Bhashith", "bhashith@company.com", "employee", "Engineering"),
        ("EMP003", "Ayesha", "ayesha@company.com", "employee", "HR"),
        ("MGR001", "Hisham", "hisham@company.com", "manager", "Engineering"),
        ("HR001", "Akshay", "akshay@company.com", "hr", "Human Resources"),
        ("IT001", "Rahul", "rahul@company.com", "it", "Information Technology"),
        ("FIN001", "Neha", "neha@company.com", "finance", "Finance"),
        ("ADMIN001", "Admin User", "admin@company.com", "admin", "Administration"),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO users (emp_id, name, email, role, department)
    VALUES (?, ?, ?, ?, ?)
    """, users)


def seed_leave_balances(cursor):
    balances = [
        ("EMP001", 12, 0, 10, 0, 12, 0),
        ("EMP002", 12, 0, 10, 0, 12, 0),
        ("EMP003", 12, 0, 10, 0, 12, 0),
        ("MGR001", 12, 0, 10, 0, 12, 0),
        ("HR001", 12, 0, 10, 0, 12, 0),
        ("IT001", 12, 0, 10, 0, 12, 0),
        ("FIN001", 12, 0, 10, 0, 12, 0),
        ("ADMIN001", 12, 0, 10, 0, 12, 0),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO leave_balances (
        emp_id,
        casual_total,
        casual_used,
        sick_total,
        sick_used,
        earned_total,
        earned_used
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, balances)


def seed_inventory(cursor):
    inventory = [
        ("laptop", 5),
        ("monitor", 8),
        ("keyboard", 15),
        ("mouse", 20),
        ("vpn token", 10),
        ("software license", 7),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO inventory (asset_type, available_quantity)
    VALUES (?, ?)
    """, inventory)


def seed_known_outages(cursor):
    outages = [
        (
            "vpn",
            "VPN users may face login issues due to an active authentication outage.",
            "active"
        ),
        (
            "outlook",
            "Some users are reporting delayed email sync in Outlook.",
            "active"
        ),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO known_outages (issue_type, description, status)
    VALUES (?, ?, ?)
    """, outages)


def seed_maintenance(cursor):
    maintenance = [
        (
            "network",
            "Network maintenance is scheduled this weekend. Users may experience short interruptions.",
            "scheduled",
            "2026-05-10"
        ),
        (
            "printer",
            "Printer server maintenance is planned for the admin floor.",
            "scheduled",
            "2026-05-12"
        ),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO maintenance_schedule (
        system_name,
        description,
        status,
        maintenance_date
    )
    VALUES (?, ?, ?, ?)
    """, maintenance)


def seed_database():
    create_tables()

    conn = get_connection()
    cursor = conn.cursor()

    seed_users(cursor)
    seed_leave_balances(cursor)
    seed_inventory(cursor)
    seed_known_outages(cursor)
    seed_maintenance(cursor)

    conn.commit()
    conn.close()

    print("Database seeded successfully.")


if __name__ == "__main__":
    seed_database()