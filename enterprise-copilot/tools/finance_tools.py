"""
Finance tools for payslips, reimbursements, and tax queries.
"""
import datetime

from langchain.tools import tool

import db.crud as crud
from db.database import SessionLocal

EXPENSE_LIMITS: dict = {
    "travel": 5000.0,
    "internet": 1000.0,
    "food": 500.0,
    "client_meeting": 5000.0,
}


def _get_db():
    return SessionLocal()


def _format_payslip(p) -> str:
    month_name = datetime.date(p.year, p.month, 1).strftime("%B")
    return (
        f"Payslip — {month_name} {p.year}\n"
        f"{'─'*35}\n"
        f"  Basic Salary     : ₹{p.basic_salary:>10,.2f}\n"
        f"  HRA              : ₹{p.hra:>10,.2f}\n"
        f"  Allowances       : ₹{p.allowances:>10,.2f}\n"
        f"  {'─'*31}\n"
        f"  Gross Salary     : ₹{p.gross_salary:>10,.2f}\n"
        f"  PF Deduction     : ₹{p.pf_deduction:>10,.2f}\n"
        f"  Tax Deduction    : ₹{p.tax_deduction:>10,.2f}\n"
        f"  Other Deductions : ₹{p.other_deductions:>10,.2f}\n"
        f"  {'─'*31}\n"
        f"  Net Salary       : ₹{p.net_salary:>10,.2f}\n"
    )


@tool
def get_latest_payslip(user_id: int) -> str:
    """
    Get the most recent payslip for an employee.

    Args:
        user_id: Employee DB ID.

    Returns:
        Formatted payslip string.
    """
    db = _get_db()
    try:
        payslips = crud.get_payslips_by_employee(db, user_id)
        if not payslips:
            return "No payslips found. Contact finance@company.com."
        return _format_payslip(payslips[0])
    finally:
        db.close()


@tool
def get_payslip_by_month(user_id: int, month: int, year: int) -> str:
    """
    Get a payslip for a specific month and year.

    Args:
        user_id: Employee DB ID.
        month: Month number 1-12.
        year: Four-digit year.

    Returns:
        Formatted payslip string.
    """
    db = _get_db()
    try:
        p = crud.get_payslip(db, user_id, month, year)
        if not p:
            month_name = datetime.date(year, month, 1).strftime("%B")
            return f"No payslip for {month_name} {year}. Contact finance@company.com."
        return _format_payslip(p)
    finally:
        db.close()


@tool
def get_salary_summary(user_id: int) -> str:
    """
    Get an annual CTC breakdown and year-to-date salary summary.

    Args:
        user_id: Employee DB ID.

    Returns:
        Formatted salary summary string.
    """
    db = _get_db()
    try:
        current_year = datetime.datetime.utcnow().year
        payslips = crud.get_payslips_by_employee(db, user_id)
        if not payslips:
            return "No salary data available. Contact finance@company.com."
        ytd = [p for p in payslips if p.year == current_year]
        latest = payslips[0]
        return (
            f"Salary Summary\n{'─'*35}\n"
            f"  Monthly Gross (latest) : ₹{latest.gross_salary:,.2f}\n"
            f"  Monthly Net (latest)   : ₹{latest.net_salary:,.2f}\n"
            f"  Annual CTC (projected) : ₹{latest.gross_salary * 12:,.2f}\n"
            f"  Annual Net (projected) : ₹{latest.net_salary * 12:,.2f}\n"
            f"{'─'*35}\n"
            f"  YTD Gross ({current_year})       : ₹{sum(p.gross_salary for p in ytd):,.2f}\n"
            f"  YTD Net ({current_year})         : ₹{sum(p.net_salary for p in ytd):,.2f}\n"
            f"  Months processed       : {len(ytd)}\n"
        )
    finally:
        db.close()


@tool
def submit_reimbursement(user_id: int, expense_type: str, amount: float, description: str) -> dict:
    """
    Submit a reimbursement claim. Validates amount against policy limits.

    Args:
        user_id: Employee DB ID.
        expense_type: travel, internet, food, or client_meeting.
        amount: Amount in INR.
        description: Expense description.

    Returns:
        Dict with success, reimbursement_id, message, requires_approval.
    """
    db = _get_db()
    try:
        limit = EXPENSE_LIMITS.get(expense_type.lower())
        if limit is not None and amount > limit:
            return {
                "success": False, "reimbursement_id": None, "requires_approval": False,
                "message": f"Amount ₹{amount:,.2f} exceeds the policy limit of ₹{limit:,.2f} for '{expense_type}'. Please contact Finance for exceptions.",
            }
        r = crud.create_reimbursement(db, user_id, expense_type, amount, description)
        requires_approval = amount > 500
        return {
            "success": True, "reimbursement_id": r.id, "requires_approval": requires_approval,
            "message": f"✅ Reimbursement #{r.id} submitted!\n  Type: {expense_type} | Amount: ₹{amount:,.2f}\n  Status: Pending Approval",
        }
    finally:
        db.close()


@tool
def get_reimbursement_status(user_id: int) -> str:
    """
    Get all reimbursement requests for an employee.

    Args:
        user_id: Employee DB ID.

    Returns:
        Formatted list of reimbursements and their statuses.
    """
    db = _get_db()
    try:
        reimbursements = crud.get_reimbursements_by_employee(db, user_id)
        if not reimbursements:
            return "No reimbursement requests found."
        lines = [f"Your Reimbursements ({len(reimbursements)}):\n"]
        for r in reimbursements:
            lines.append(f"  #{r.id}: {r.expense_type.title()} | ₹{r.amount:,.2f} | {r.status.upper()} | {r.created_at.strftime('%Y-%m-%d')}")
            lines.append(f"    {r.description}")
        return "\n".join(lines)
    finally:
        db.close()


@tool
def get_tax_info(user_id: int) -> str:
    """
    Get a tax deduction summary for the current financial year.

    Args:
        user_id: Employee DB ID.

    Returns:
        Formatted tax summary string.
    """
    db = _get_db()
    try:
        now = datetime.datetime.utcnow()
        fy_year = now.year if now.month >= 4 else now.year - 1
        payslips = crud.get_payslips_by_employee(db, user_id)
        fy = [p for p in payslips if (p.year == fy_year and p.month >= 4) or (p.year == fy_year + 1 and p.month <= 3)]
        if not fy:
            return f"No payslip data for FY {fy_year}-{str(fy_year+1)[-2:]}. Contact finance@company.com."
        latest = fy[0]
        return (
            f"Tax Summary — FY {fy_year}-{str(fy_year+1)[-2:]}\n{'─'*35}\n"
            f"  Months Processed     : {len(fy)}\n"
            f"  YTD Gross Salary     : ₹{sum(p.gross_salary for p in fy):,.2f}\n"
            f"  YTD TDS (Income Tax) : ₹{sum(p.tax_deduction for p in fy):,.2f}\n"
            f"  YTD PF Deduction     : ₹{sum(p.pf_deduction for p in fy):,.2f}\n"
            f"{'─'*35}\n"
            f"  Monthly TDS (latest) : ₹{latest.tax_deduction:,.2f}\n"
            f"  Monthly PF (latest)  : ₹{latest.pf_deduction:,.2f}\n"
            f"\n📌 Investment declaration deadline: January 31st\n"
            f"   Contact: finance@company.com"
        )
    finally:
        db.close()
