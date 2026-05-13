from database.db import get_connection


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Users table for RBAC
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        emp_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT,
        role TEXT NOT NULL,
        department TEXT
    )
    """)

    # Leave balances
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leave_balances (
        emp_id TEXT PRIMARY KEY,
        casual_total INTEGER DEFAULT 12,
        casual_used INTEGER DEFAULT 0,
        sick_total INTEGER DEFAULT 10,
        sick_used INTEGER DEFAULT 0,
        earned_total INTEGER DEFAULT 12,
        earned_used INTEGER DEFAULT 0,
        FOREIGN KEY (emp_id) REFERENCES users(emp_id)
    )
    """)

    # Leave requests
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leave_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT NOT NULL,
        leave_type TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        manager_comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (emp_id) REFERENCES users(emp_id)
    )
    """)

    # IT tickets
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS it_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        description TEXT,
        priority TEXT DEFAULT 'medium',
        status TEXT DEFAULT 'open',
        assigned_engineer TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (emp_id) REFERENCES users(emp_id)
    )
    """)

    # Known outages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS known_outages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_type TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Maintenance schedule
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        system_name TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'scheduled',
        maintenance_date TEXT
    )
    """)

    # Inventory
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_type TEXT UNIQUE NOT NULL,
        available_quantity INTEGER DEFAULT 0
    )
    """)

    # Asset requests
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS asset_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT NOT NULL,
        asset_type TEXT NOT NULL,
        reason TEXT,
        manager_approval TEXT DEFAULT 'pending',
        it_approval TEXT DEFAULT 'pending',
        inventory_status TEXT DEFAULT 'pending',
        status TEXT DEFAULT 'pending_manager_approval',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (emp_id) REFERENCES users(emp_id)
    )
    """)

    # Reimbursement requests
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reimbursements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT NOT NULL,
        claim_type TEXT NOT NULL,
        amount REAL NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'pending',
        finance_comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (emp_id) REFERENCES users(emp_id)
    )
    """)

    # Chat memory
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        user_message TEXT,
        assistant_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # System logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT,
        user_query TEXT,
        intent TEXT,
        agent_used TEXT,
        tool_used TEXT,
        status TEXT,
        response_time REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    print("Database tables created successfully.")


if __name__ == "__main__":
    create_tables()