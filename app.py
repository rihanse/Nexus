from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from graph import run_workflow
from database.db import get_connection
from tools.log_tools import get_recent_logs


app = FastAPI(
    title="Workplace Buddy",
    description="Enterprise Multi-Agent AI Copilot for HR, IT, and Finance Operations",
    version="1.0.0"
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    emp_id: str
    message: str
    chat_history: Optional[List[ChatMessage]] = None


@app.get("/", response_class=HTMLResponse)
def home():
    index_path = FRONTEND_DIR / "index.html"

    if not index_path.exists():
        return HTMLResponse("<h1>frontend/index.html not found</h1>", status_code=404)

    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.get("/api/users")
def get_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT emp_id, name, role, department, email
    FROM users
    ORDER BY role, emp_id
    """)

    rows = cursor.fetchall()
    conn.close()

    return {
        "success": True,
        "users": [dict(row) for row in rows]
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    if not request.emp_id.strip():
        raise HTTPException(status_code=400, detail="Employee ID is required.")

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message is required.")

    chat_history = [
        {
            "role": item.role,
            "content": item.content
        }
        for item in request.chat_history
    ] if request.chat_history else []

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT emp_id, name, role, department FROM users WHERE emp_id = ?", (request.emp_id,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    result = run_workflow(
        user_input=request.message,
        emp_id=user["emp_id"],
        name=user["name"],
        role=user["role"],
        department=user["department"],
        chat_history=chat_history
    )

    return {
        "success": True,
        "response": result["response"],
        "intent": result.get("intent"),
        "agent": result.get("agent"),
        "tool_used": result.get("tool_used"),
        "status": result.get("status"),
        "role": result.get("role"),
        "response_time": result.get("response_time")
    }


@app.get("/api/logs")
def logs():
    return {
        "success": True,
        "logs": get_recent_logs(10)
    }


@app.get("/api/health")
def health():
    return {
        "success": True,
        "message": "Workplace Buddy API is running."
    }