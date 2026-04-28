"""
SQLAlchemy ORM models for the Enterprise Copilot system.
"""
import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from db.database import Base


class User(Base):
    """User model representing all employees and team members."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    department = Column(String, nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    manager = relationship("User", remote_side=[id], backref="subordinates")
    leave_requests = relationship("LeaveRequest", foreign_keys="LeaveRequest.employee_id", back_populates="employee")
    leave_balances = relationship("LeaveBalance", back_populates="employee")
    it_tickets = relationship("ITTicket", foreign_keys="ITTicket.employee_id", back_populates="employee")
    asset_requests = relationship("AssetRequest", back_populates="employee")
    reimbursements = relationship("Reimbursement", foreign_keys="Reimbursement.employee_id", back_populates="employee")
    payslips = relationship("Payslip", back_populates="employee")


class LeaveRequest(Base):
    """Leave request model."""
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leave_type = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_days = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)
    status = Column(String, default="pending")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approval_comment = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    employee = relationship("User", foreign_keys=[employee_id], back_populates="leave_requests")
    approver = relationship("User", foreign_keys=[approver_id])


class LeaveBalance(Base):
    """Leave balance per employee per year."""
    __tablename__ = "leave_balances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    leave_type = Column(String, nullable=False)
    total_allowed = Column(Integer, nullable=False)
    used = Column(Integer, default=0)
    remaining = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)

    employee = relationship("User", back_populates="leave_balances")


class ITTicket(Base):
    """IT support ticket model."""
    __tablename__ = "it_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String, unique=True, index=True, nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    issue_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    status = Column(String, default="open")
    assigned_engineer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    employee = relationship("User", foreign_keys=[employee_id], back_populates="it_tickets")
    assigned_engineer = relationship("User", foreign_keys=[assigned_engineer_id])


class AssetRequest(Base):
    """Asset request model."""
    __tablename__ = "asset_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    asset_type = Column(String, nullable=False)
    asset_name = Column(String, nullable=False)
    justification = Column(String, nullable=False)
    status = Column(String, default="pending_manager")
    manager_approval = Column(String, nullable=True)
    it_approval = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    employee = relationship("User", back_populates="asset_requests")


class KnownOutage(Base):
    """Known IT service outage model."""
    __tablename__ = "known_outages"

    id = Column(Integer, primary_key=True, index=True)
    service = Column(String, nullable=False)
    description = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)


class Reimbursement(Base):
    """Expense reimbursement request model."""
    __tablename__ = "reimbursements"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expense_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    receipt_path = Column(String, nullable=True)
    status = Column(String, default="pending")
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    employee = relationship("User", foreign_keys=[employee_id], back_populates="reimbursements")
    approver = relationship("User", foreign_keys=[approver_id])


class Payslip(Base):
    """Monthly payslip model."""
    __tablename__ = "payslips"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    basic_salary = Column(Float, nullable=False)
    hra = Column(Float, nullable=False)
    allowances = Column(Float, nullable=False)
    gross_salary = Column(Float, nullable=False)
    pf_deduction = Column(Float, nullable=False)
    tax_deduction = Column(Float, nullable=False)
    other_deductions = Column(Float, nullable=False)
    net_salary = Column(Float, nullable=False)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)

    employee = relationship("User", back_populates="payslips")
