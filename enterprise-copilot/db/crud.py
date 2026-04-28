"""
CRUD operations for all database models in the Enterprise Copilot system.
"""
import datetime
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from db.models import (
    AssetRequest,
    ITTicket,
    KnownOutage,
    LeaveBalance,
    LeaveRequest,
    Payslip,
    Reimbursement,
    User,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─────────────────────────────────────────────
# USER CRUD
# ─────────────────────────────────────────────

def create_user(
    db: Session,
    employee_id: str,
    name: str,
    email: str,
    password: str,
    role: str,
    department: str,
    manager_id: Optional[int] = None,
) -> User:
    """Create and persist a new user with a hashed password."""
    hashed = pwd_context.hash(password)
    user = User(
        employee_id=employee_id,
        name=name,
        email=email,
        hashed_password=hashed,
        role=role,
        department=department,
        manager_id=manager_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Retrieve a user by their primary key ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Retrieve a user by their email address."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_employee_id(db: Session, employee_id: str) -> Optional[User]:
    """Retrieve a user by their employee ID string (e.g., 'EMP001')."""
    return db.query(User).filter(User.employee_id == employee_id).first()


def authenticate_user(db: Session, employee_id: str, password: str) -> Optional[User]:
    """
    Authenticate a user by employee ID and plain-text password.
    Returns the User object on success, or None on failure.
    """
    user = get_user_by_employee_id(db, employee_id)
    if not user:
        return None
    if not pwd_context.verify(password, user.hashed_password):
        return None
    return user


def get_all_users(db: Session) -> list[User]:
    """Return all users in the system."""
    return db.query(User).all()


# ─────────────────────────────────────────────
# LEAVE REQUEST CRUD
# ─────────────────────────────────────────────

def create_leave_request(
    db: Session,
    employee_id: int,
    leave_type: str,
    start_date: datetime.date,
    end_date: datetime.date,
    total_days: int,
    reason: str,
) -> LeaveRequest:
    """Create a new leave request with status 'pending'."""
    req = LeaveRequest(
        employee_id=employee_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        reason=reason,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def get_leave_requests_by_employee(db: Session, employee_id: int) -> list[LeaveRequest]:
    """Return all leave requests for a specific employee, ordered by most recent."""
    return (
        db.query(LeaveRequest)
        .filter(LeaveRequest.employee_id == employee_id)
        .order_by(LeaveRequest.created_at.desc())
        .all()
    )


def get_leave_request_by_id(db: Session, request_id: int) -> Optional[LeaveRequest]:
    """Return a single leave request by its ID."""
    return db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()


def update_leave_status(
    db: Session,
    request_id: int,
    status: str,
    approver_id: Optional[int] = None,
    comment: Optional[str] = None,
) -> Optional[LeaveRequest]:
    """Update the status, approver, and optional comment on a leave request."""
    req = get_leave_request_by_id(db, request_id)
    if not req:
        return None
    req.status = status
    req.updated_at = datetime.datetime.utcnow()
    if approver_id is not None:
        req.approver_id = approver_id
    if comment is not None:
        req.approval_comment = comment
    db.commit()
    db.refresh(req)
    return req


def check_overlapping_leave(
    db: Session,
    employee_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
) -> Optional[LeaveRequest]:
    """
    Check if there is any active (pending/approved) leave request that
    overlaps with the given date range for an employee.
    """
    return (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(["pending", "approved"]),
            LeaveRequest.start_date <= end_date,
            LeaveRequest.end_date >= start_date,
        )
        .first()
    )


def get_pending_approvals_for_manager(db: Session, manager_id: int) -> list[LeaveRequest]:
    """Return all pending leave requests from employees who report to this manager."""
    subordinate_ids = [
        u.id for u in db.query(User).filter(User.manager_id == manager_id).all()
    ]
    if not subordinate_ids:
        return []
    return (
        db.query(LeaveRequest)
        .filter(
            LeaveRequest.employee_id.in_(subordinate_ids),
            LeaveRequest.status == "pending",
        )
        .order_by(LeaveRequest.created_at.asc())
        .all()
    )


# ─────────────────────────────────────────────
# LEAVE BALANCE CRUD
# ─────────────────────────────────────────────

def get_leave_balance(
    db: Session, employee_id: int, leave_type: str, year: Optional[int] = None
) -> Optional[LeaveBalance]:
    """Return the leave balance for a specific employee, type, and year."""
    if year is None:
        year = datetime.datetime.utcnow().year
    return (
        db.query(LeaveBalance)
        .filter(
            LeaveBalance.employee_id == employee_id,
            LeaveBalance.leave_type == leave_type,
            LeaveBalance.year == year,
        )
        .first()
    )


def update_leave_balance(
    db: Session, employee_id: int, leave_type: str, days_used: int, year: Optional[int] = None
) -> Optional[LeaveBalance]:
    """Increment the used days and decrement the remaining days for a leave balance."""
    if year is None:
        year = datetime.datetime.utcnow().year
    balance = get_leave_balance(db, employee_id, leave_type, year)
    if not balance:
        return None
    balance.used += days_used
    balance.remaining -= days_used
    db.commit()
    db.refresh(balance)
    return balance


def initialize_leave_balances(
    db: Session,
    employee_id: int,
    year: Optional[int] = None,
    casual: int = 10,
    sick: int = 7,
    annual: int = 15,
) -> list[LeaveBalance]:
    """
    Initialize standard leave balances for a new employee for the given year.
    Returns the list of created LeaveBalance records.
    """
    if year is None:
        year = datetime.datetime.utcnow().year
    balances = []
    for ltype, total in [("casual", casual), ("sick", sick), ("annual", annual)]:
        existing = get_leave_balance(db, employee_id, ltype, year)
        if not existing:
            b = LeaveBalance(
                employee_id=employee_id,
                leave_type=ltype,
                total_allowed=total,
                used=0,
                remaining=total,
                year=year,
            )
            db.add(b)
            balances.append(b)
    db.commit()
    return balances


# ─────────────────────────────────────────────
# IT TICKET CRUD
# ─────────────────────────────────────────────

def create_ticket(
    db: Session,
    employee_id: int,
    issue_type: str,
    title: str,
    description: str,
    priority: str,
) -> ITTicket:
    """Create a new IT support ticket with an auto-generated ticket number."""
    year = datetime.datetime.utcnow().year
    count = db.query(ITTicket).count() + 1
    ticket_number = f"TKT-{year}-{count:03d}"
    ticket = ITTicket(
        ticket_number=ticket_number,
        employee_id=employee_id,
        issue_type=issue_type,
        title=title,
        description=description,
        priority=priority,
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket_by_id(db: Session, ticket_id: int) -> Optional[ITTicket]:
    """Return a single IT ticket by its primary key."""
    return db.query(ITTicket).filter(ITTicket.id == ticket_id).first()


def get_tickets_by_employee(db: Session, employee_id: int) -> list[ITTicket]:
    """Return all IT tickets raised by a specific employee."""
    return (
        db.query(ITTicket)
        .filter(ITTicket.employee_id == employee_id)
        .order_by(ITTicket.created_at.desc())
        .all()
    )


def get_all_tickets(db: Session) -> list[ITTicket]:
    """Return all IT tickets across all employees."""
    return db.query(ITTicket).order_by(ITTicket.created_at.desc()).all()


def update_ticket_status(
    db: Session, ticket_id: int, status: str, resolution_notes: Optional[str] = None
) -> Optional[ITTicket]:
    """Update the status and optional resolution notes of an IT ticket."""
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None
    ticket.status = status
    ticket.updated_at = datetime.datetime.utcnow()
    if resolution_notes:
        ticket.resolution_notes = resolution_notes
    db.commit()
    db.refresh(ticket)
    return ticket


def assign_ticket(db: Session, ticket_id: int, engineer_id: int) -> Optional[ITTicket]:
    """Assign an IT ticket to an engineer and mark it as in_progress."""
    ticket = get_ticket_by_id(db, ticket_id)
    if not ticket:
        return None
    ticket.assigned_engineer_id = engineer_id
    ticket.status = "in_progress"
    ticket.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return ticket


def get_open_tickets_by_issue_type(db: Session, issue_type: str, employee_id: int) -> list[ITTicket]:
    """Return open tickets for a specific employee and issue type."""
    return (
        db.query(ITTicket)
        .filter(
            ITTicket.employee_id == employee_id,
            ITTicket.issue_type == issue_type,
            ITTicket.status.in_(["open", "in_progress"]),
        )
        .all()
    )


# ─────────────────────────────────────────────
# ASSET REQUEST CRUD
# ─────────────────────────────────────────────

def create_asset_request(
    db: Session,
    employee_id: int,
    asset_type: str,
    asset_name: str,
    justification: str,
) -> AssetRequest:
    """Create a new asset request with status 'pending_manager'."""
    req = AssetRequest(
        employee_id=employee_id,
        asset_type=asset_type,
        asset_name=asset_name,
        justification=justification,
        status="pending_manager",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def get_asset_requests_by_employee(db: Session, employee_id: int) -> list[AssetRequest]:
    """Return all asset requests for a specific employee."""
    return (
        db.query(AssetRequest)
        .filter(AssetRequest.employee_id == employee_id)
        .order_by(AssetRequest.created_at.desc())
        .all()
    )


def update_asset_status(
    db: Session,
    request_id: int,
    status: str,
    manager_approval: Optional[str] = None,
    it_approval: Optional[str] = None,
) -> Optional[AssetRequest]:
    """Update the status and approval fields of an asset request."""
    req = db.query(AssetRequest).filter(AssetRequest.id == request_id).first()
    if not req:
        return None
    req.status = status
    if manager_approval is not None:
        req.manager_approval = manager_approval
    if it_approval is not None:
        req.it_approval = it_approval
    db.commit()
    db.refresh(req)
    return req


# ─────────────────────────────────────────────
# KNOWN OUTAGE CRUD
# ─────────────────────────────────────────────

def get_active_outages(db: Session) -> list[KnownOutage]:
    """Return all currently active known outages."""
    return db.query(KnownOutage).filter(KnownOutage.is_active == True).all()


def create_outage(
    db: Session, service: str, description: str, start_time: datetime.datetime
) -> KnownOutage:
    """Create a new known outage record."""
    outage = KnownOutage(
        service=service,
        description=description,
        start_time=start_time,
        is_active=True,
    )
    db.add(outage)
    db.commit()
    db.refresh(outage)
    return outage


def resolve_outage(db: Session, outage_id: int) -> Optional[KnownOutage]:
    """Mark a known outage as resolved by setting is_active=False and end_time."""
    outage = db.query(KnownOutage).filter(KnownOutage.id == outage_id).first()
    if not outage:
        return None
    outage.is_active = False
    outage.end_time = datetime.datetime.utcnow()
    db.commit()
    db.refresh(outage)
    return outage


# ─────────────────────────────────────────────
# REIMBURSEMENT CRUD
# ─────────────────────────────────────────────

def create_reimbursement(
    db: Session,
    employee_id: int,
    expense_type: str,
    amount: float,
    description: str,
    receipt_path: Optional[str] = None,
) -> Reimbursement:
    """Create a new reimbursement request with status 'pending'."""
    r = Reimbursement(
        employee_id=employee_id,
        expense_type=expense_type,
        amount=amount,
        description=description,
        receipt_path=receipt_path,
        status="pending",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def get_reimbursements_by_employee(db: Session, employee_id: int) -> list[Reimbursement]:
    """Return all reimbursement requests for a specific employee."""
    return (
        db.query(Reimbursement)
        .filter(Reimbursement.employee_id == employee_id)
        .order_by(Reimbursement.created_at.desc())
        .all()
    )


def update_reimbursement_status(
    db: Session,
    reimbursement_id: int,
    status: str,
    approver_id: Optional[int] = None,
) -> Optional[Reimbursement]:
    """Update the status and approver of a reimbursement request."""
    r = db.query(Reimbursement).filter(Reimbursement.id == reimbursement_id).first()
    if not r:
        return None
    r.status = status
    if approver_id is not None:
        r.approver_id = approver_id
    db.commit()
    db.refresh(r)
    return r


# ─────────────────────────────────────────────
# PAYSLIP CRUD
# ─────────────────────────────────────────────

def get_payslip(db: Session, employee_id: int, month: int, year: int) -> Optional[Payslip]:
    """Return the payslip for a specific employee, month, and year."""
    return (
        db.query(Payslip)
        .filter(
            Payslip.employee_id == employee_id,
            Payslip.month == month,
            Payslip.year == year,
        )
        .first()
    )


def get_payslips_by_employee(db: Session, employee_id: int) -> list[Payslip]:
    """Return all payslips for a specific employee ordered by most recent."""
    return (
        db.query(Payslip)
        .filter(Payslip.employee_id == employee_id)
        .order_by(Payslip.year.desc(), Payslip.month.desc())
        .all()
    )


# ─────────────────────────────────────────────
# SEED DATABASE
# ─────────────────────────────────────────────

def seed_database(db: Session) -> None:
    """
    Seed the database with test users, leave balances, IT tickets,
    a payslip, and a known outage. Safe to call multiple times — skips
    if data already exists.
    """
    # Skip if already seeded
    if db.query(User).count() > 0:
        print("Database already seeded. Skipping.")
        return

    print("Seeding database with test data...")

    # Create 6 users
    admin = create_user(db, "EMP000", "Admin User", "admin@company.com", "password123", "admin", "IT")
    alice = create_user(db, "EMP001", "Alice Johnson", "alice@company.com", "password123", "employee", "Engineering")
    bob = create_user(db, "EMP002", "Bob Smith", "bob@company.com", "password123", "manager", "Engineering")
    carol = create_user(db, "EMP003", "Carol White", "carol@company.com", "password123", "hr_team", "HR")
    dave = create_user(db, "EMP004", "Dave Brown", "dave@company.com", "password123", "it_team", "IT")
    eve = create_user(db, "EMP005", "Eve Davis", "eve@company.com", "password123", "finance_team", "Finance")

    # Set alice's manager to bob
    alice.manager_id = bob.id
    db.commit()

    # Leave balances for alice (current year)
    initialize_leave_balances(db, alice.id, casual=10, sick=7, annual=15)

    # 2 sample IT tickets for alice
    ticket1 = ITTicket(
        ticket_number=f"TKT-{datetime.datetime.utcnow().year}-001",
        employee_id=alice.id,
        issue_type="vpn",
        title="VPN Connection Dropping",
        description="My VPN keeps disconnecting every 30 minutes.",
        priority="high",
        status="open",
        created_at=datetime.datetime.utcnow() - datetime.timedelta(days=2),
        updated_at=datetime.datetime.utcnow() - datetime.timedelta(days=2),
    )
    ticket2 = ITTicket(
        ticket_number=f"TKT-{datetime.datetime.utcnow().year}-002",
        employee_id=alice.id,
        issue_type="laptop",
        title="Laptop Running Slow",
        description="My laptop has been very slow after the latest OS update.",
        priority="medium",
        status="in_progress",
        assigned_engineer_id=dave.id,
        created_at=datetime.datetime.utcnow() - datetime.timedelta(days=5),
        updated_at=datetime.datetime.utcnow() - datetime.timedelta(days=1),
    )
    db.add(ticket1)
    db.add(ticket2)

    # 1 sample payslip for alice (June 2024)
    payslip = Payslip(
        employee_id=alice.id,
        month=6,
        year=2024,
        basic_salary=50000.0,
        hra=20000.0,
        allowances=10000.0,
        gross_salary=80000.0,
        pf_deduction=6000.0,
        tax_deduction=8000.0,
        other_deductions=1000.0,
        net_salary=65000.0,
        generated_at=datetime.datetime(2024, 6, 30),
    )
    db.add(payslip)

    # 1 known outage for VPN
    outage = KnownOutage(
        service="vpn",
        description="Company-wide VPN service degradation affecting all remote connections. Our team is actively working on a fix.",
        start_time=datetime.datetime.utcnow() - datetime.timedelta(hours=3),
        is_active=True,
    )
    db.add(outage)

    db.commit()
    print("✅ Database seeded successfully!")
    print("  Users: admin, alice (EMP001), bob (EMP002), carol (EMP003), dave (EMP004), eve (EMP005)")
    print("  All passwords: password123")
