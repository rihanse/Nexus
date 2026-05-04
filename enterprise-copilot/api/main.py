"""
FastAPI application — Enterprise Multi-Agent AI Copilot.
"""
import os
import sys

# Patch SSL certificates for corporate proxies on Windows
try:
    import certifi_win32.bootstrapping
    certifi_win32.bootstrapping.bootstrap()
except ImportError:
    pass

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "enterprise-copilot")

import db.crud as crud
from agents.approval_agent import approval_manager
from agents.router_agent import run_graph
from agents.state import AgentState
from db.database import Base, SessionLocal, engine, get_db
from db.models import User
from middleware.auth import get_current_user, require_role


# ── Lifespan ─────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        crud.seed_database(db)
    finally:
        db.close()
    try:
        from rag.ingest import ingest_documents
        index_path = os.path.join(os.getenv("FAISS_INDEX_DIR", "./faiss_index"), "index.faiss")
        if not os.path.exists(index_path):
            print("[INFO] No FAISS index found. Running initial ingestion...")
            ingest_documents()
        else:
            print("[INFO] FAISS index found. Skipping ingestion.")
    except Exception as e:
        print(f"[WARN] RAG ingestion failed: {e}")
    yield
    print("Enterprise Copilot shutting down.")


# ── App ──────────────────────────────────────
app = FastAPI(
    title="Enterprise Multi-Agent AI Copilot",
    description="AI-powered copilot for HR, IT, and Finance operations.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


# ── Pydantic Models ───────────────────────────
class LoginRequest(BaseModel):
    employee_id: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    requires_approval: bool
    session_id: str

class LeaveApplyRequest(BaseModel):
    leave_type: str
    start_date: str
    end_date: str
    reason: str

class ApprovalRequest(BaseModel):
    decision: str
    comment: str = ""

class ReimbursementRequest(BaseModel):
    expense_type: str
    amount: float
    description: str


@app.get("/auth/me", tags=["Auth"])
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently simulated user's profile."""
    return {
        "id": current_user.id,
        "employee_id": current_user.employee_id,
        "name": current_user.name,
        "role": current_user.role,
        "department": current_user.department,
        "email": current_user.email,
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health check — no auth required."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Chat ─────────────────────────────────────
@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Route a user message through the multi-agent LangGraph system."""
    initial_state: AgentState = {
        "messages": [HumanMessage(content=request.message)],
        "user_id": current_user.id,
        "user_role": current_user.role,
        "user_department": current_user.department,
        "user_name": current_user.name,
        "user_email": current_user.email,
        "intent": "",
        "current_agent": "",
        "requires_approval": False,
        "approval_request_id": None,
        "approval_type": None,
        "final_response": "",
        "error": None,
    }
    try:
        result = run_graph(initial_state)
        return ChatResponse(
            response=result.get("final_response", "I could not process your request."),
            requires_approval=result.get("requires_approval", False),
            session_id=request.session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(exc)}")


# ── Leave ─────────────────────────────────────
@app.get("/leave/balance", tags=["Leave"])
def get_leave_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all leave balances for the authenticated user."""
    import datetime as dt
    year = dt.datetime.utcnow().year
    balances = []
    for lt in ("casual", "sick", "annual"):
        b = crud.get_leave_balance(db, current_user.id, lt, year)
        if b:
            balances.append({"leave_type": b.leave_type, "total_allowed": b.total_allowed,
                             "used": b.used, "remaining": b.remaining, "year": b.year})
    return {"balances": balances, "employee": current_user.name}


@app.post("/leave/apply", tags=["Leave"])
def apply_leave(request: LeaveApplyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Apply for leave via REST API."""
    from tools.hr_tools import apply_leave as _apply
    return _apply.invoke({"user_id": current_user.id, "leave_type": request.leave_type,
                          "start_date": request.start_date, "end_date": request.end_date, "reason": request.reason})


# ── Approvals ─────────────────────────────────
@app.get("/approvals/pending", tags=["Approvals"])
def get_pending_approvals(current_user: User = Depends(get_current_user)):
    """Get all pending approvals assigned to the current user."""
    pending = approval_manager.get_pending_approvals(current_user.id)
    return {"pending": pending}


@app.post("/approve/{request_id}", tags=["Approvals"])
def process_approval(request_id: int, body: ApprovalRequest,
                     current_user: User = Depends(require_role("manager", "hr_team", "it_team", "finance_team", "admin")),
                     db: Session = Depends(get_db)):
    """Approve or reject a pending request (managers/team leads only)."""
    result = approval_manager.process_approval(
        approval_id=request_id, decision=body.decision,
        comment=body.comment, approver_id=current_user.id, db=db)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


# ── IT Tickets ────────────────────────────────
@app.get("/tickets/my", tags=["IT Tickets"])
def get_my_tickets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all IT tickets for the authenticated user."""
    tickets = crud.get_tickets_by_employee(db, current_user.id)
    return {"tickets": [{"id": t.id, "ticket_number": t.ticket_number, "issue_type": t.issue_type,
                         "title": t.title, "priority": t.priority, "status": t.status,
                         "created_at": t.created_at.isoformat()} for t in tickets]}


@app.get("/tickets/all", tags=["IT Tickets"])
def get_all_tickets(current_user: User = Depends(require_role("it_team", "admin")), db: Session = Depends(get_db)):
    """Get all IT tickets system-wide (IT team / admin only)."""
    tickets = crud.get_all_tickets(db)
    return {"tickets": [{"id": t.id, "ticket_number": t.ticket_number, "employee_id": t.employee_id,
                         "issue_type": t.issue_type, "title": t.title, "priority": t.priority,
                         "status": t.status, "created_at": t.created_at.isoformat()} for t in tickets]}


# ── Finance ───────────────────────────────────
@app.post("/reimbursement/submit", tags=["Finance"])
def submit_reimbursement(request: ReimbursementRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Submit a reimbursement claim."""
    from tools.finance_tools import submit_reimbursement as _submit
    return _submit.invoke({"user_id": current_user.id, "expense_type": request.expense_type,
                           "amount": request.amount, "description": request.description})


# ── Admin ─────────────────────────────────────
@app.get("/admin/users", tags=["Admin"])
def get_all_users(current_user: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    """List all users — admin only."""
    users = crud.get_all_users(db)
    return {"users": [{"id": u.id, "employee_id": u.employee_id, "name": u.name, "email": u.email,
                       "role": u.role, "department": u.department, "manager_id": u.manager_id} for u in users]}
