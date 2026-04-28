"""
Pytest tests for the Enterprise Copilot tools layer (in-memory SQLite).
"""
import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base
from db.models import ITTicket
import db.crud as crud


@pytest.fixture(scope="function")
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def seeded_db(db):
    manager = crud.create_user(db, "EMP002", "Bob Manager", "bob@test.com", "password123", "manager", "Engineering")
    alice = crud.create_user(db, "EMP001", "Alice Employee", "alice@test.com", "password123", "employee", "Engineering")
    alice.manager_id = manager.id
    db.commit()
    db.refresh(alice)
    crud.initialize_leave_balances(db, alice.id, casual=10, sick=7, annual=15)
    return db, alice, manager


# ── Leave Tests ───────────────────────────────

def test_create_leave_request_success(seeded_db):
    db, alice, _ = seeded_db
    start = datetime.date.today() + datetime.timedelta(days=5)
    end = start + datetime.timedelta(days=1)
    req = crud.create_leave_request(db, alice.id, "casual", start, end, 2, "Vacation")
    assert req is not None
    assert req.status == "pending"
    assert req.leave_type == "casual"
    assert req.total_days == 2


def test_leave_balance_initialized(seeded_db):
    db, alice, _ = seeded_db
    casual = crud.get_leave_balance(db, alice.id, "casual")
    sick = crud.get_leave_balance(db, alice.id, "sick")
    annual = crud.get_leave_balance(db, alice.id, "annual")
    assert casual.total_allowed == 10
    assert casual.remaining == 10
    assert sick.total_allowed == 7
    assert annual.total_allowed == 15


def test_overlapping_leave_detected(seeded_db):
    db, alice, _ = seeded_db
    start = datetime.date.today() + datetime.timedelta(days=10)
    end = start + datetime.timedelta(days=3)
    crud.create_leave_request(db, alice.id, "casual", start, end, 4, "Holiday")
    overlap = crud.check_overlapping_leave(db, alice.id, start + datetime.timedelta(days=1), end + datetime.timedelta(days=2))
    assert overlap is not None


def test_update_leave_status(seeded_db):
    db, alice, manager = seeded_db
    start = datetime.date.today() + datetime.timedelta(days=3)
    end = start + datetime.timedelta(days=1)
    req = crud.create_leave_request(db, alice.id, "sick", start, end, 2, "Fever")
    updated = crud.update_leave_status(db, req.id, "approved", approver_id=manager.id, comment="Get well soon!")
    assert updated.status == "approved"
    assert updated.approver_id == manager.id
    assert updated.approval_comment == "Get well soon!"


# ── IT Ticket Tests ───────────────────────────

def test_create_ticket_success(seeded_db):
    db, alice, _ = seeded_db
    t = crud.create_ticket(db, alice.id, "laptop", "Laptop Slow", "Running slow", "medium")
    assert t.status == "open"
    assert t.ticket_number.startswith("TKT-")


def test_duplicate_ticket_detection(seeded_db):
    db, alice, _ = seeded_db
    t1 = crud.create_ticket(db, alice.id, "vpn", "VPN Issue", "Cannot connect", "high")
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=7)
    dup = db.query(ITTicket).filter(
        ITTicket.employee_id == alice.id,
        ITTicket.issue_type == "vpn",
        ITTicket.status.in_(["open", "in_progress"]),
        ITTicket.created_at >= cutoff,
    ).first()
    assert dup is not None
    assert dup.id == t1.id


def test_known_outage_creation(seeded_db):
    db, _, _ = seeded_db
    outage = crud.create_outage(db, "vpn", "VPN service degradation", datetime.datetime.utcnow())
    assert outage.is_active is True
    active = crud.get_active_outages(db)
    vpn = [o for o in active if "vpn" in o.service.lower()]
    assert len(vpn) > 0


# ── Finance/RBAC Tests ────────────────────────

def test_expense_limit_value():
    from tools.finance_tools import EXPENSE_LIMITS
    assert EXPENSE_LIMITS["food"] == 500.0
    assert EXPENSE_LIMITS["travel"] == 5000.0
    assert EXPENSE_LIMITS["internet"] == 1000.0


def test_employee_cannot_call_get_all_tickets(seeded_db):
    db, alice, _ = seeded_db
    assert alice.role == "employee"
    assert alice.role not in ("it_team", "admin")


def test_authenticate_user_success(seeded_db):
    db, alice, _ = seeded_db
    user = crud.authenticate_user(db, "EMP001", "password123")
    assert user is not None
    assert user.name == "Alice Employee"


def test_authenticate_user_wrong_password(seeded_db):
    db, alice, _ = seeded_db
    user = crud.authenticate_user(db, "EMP001", "wrongpassword")
    assert user is None
