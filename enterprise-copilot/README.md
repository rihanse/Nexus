# 🤖 Enterprise Multi-Agent AI Copilot

An AI-powered internal assistant for **HR**, **IT**, and **Finance** operations — built with LangGraph, FastAPI, ChromaDB, and Streamlit.

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Architecture](#-architecture)
3. [Tech Stack](#-tech-stack)
4. [Project Structure](#-project-structure)
5. [Prerequisites](#-prerequisites)
6. [Installation](#-installation)
7. [Fixing the ChromaDB / chroma-hnswlib Error on Windows](#-fixing-chromadb--chroma-hnswlib-error-on-windows)
8. [Configuration (.env)](#-configuration-env)
9. [Running the Application](#-running-the-application)
10. [Test User Credentials](#-test-user-credentials)
11. [API Endpoints Reference](#-api-endpoints-reference)
12. [Using the Streamlit Frontend](#-using-the-streamlit-frontend)
13. [How to Add New Policy Documents (RAG)](#-how-to-add-new-policy-documents-rag)
14. [Setting Up Power Automate for Email Notifications](#-setting-up-power-automate-for-email-notifications)
15. [Running Tests](#-running-tests)
16. [Troubleshooting](#-troubleshooting)

---

## 🔍 Project Overview

The Enterprise AI Copilot routes employee questions through a multi-agent LangGraph pipeline that:

- **HR Agent** — Leave management (apply/cancel/approve), HR policy Q&A via RAG
- **IT Agent** — Raise tickets, track status, asset requests, outage detection
- **Finance Agent** — Payslip lookup, reimbursement claims, tax & PF summaries
- **Router Agent** — Intent classification + Role-Based Access Control (RBAC)
- **RAG** — ChromaDB-powered knowledge base supporting `.txt` and `.pdf` policy docs

---

## 🏗 Architecture

```
User ──▶ Streamlit Frontend ──▶ FastAPI (/chat)
                                      │
                              Router Agent (LangGraph)
                              ├── detect_intent (gpt-4o-mini)
                              ├── validate_role (RBAC)
                              └── route_to_agent
                                   ├── HR Agent ──▶ HR Tools + RAG (ChromaDB)
                                   ├── IT Agent ──▶ IT Tools + DB
                                   └── Finance Agent ──▶ Finance Tools + DB
                                          │
                                   handle_approval (if needed)
                                          │
                                   format_response ──▶ User
```

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Orchestration | LangGraph + LangChain |
| LLM | OpenAI `gpt-4o-mini` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | FAISS (`faiss-cpu`) |
| Relational DB | SQLite + SQLAlchemy |
| API | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Tool Server | FastMCP |
| Authentication | JWT (`python-jose` + `passlib`) |
| Email | Power Automate HTTP Trigger |
| Tracing | LangSmith |

---

## 📂 Project Structure

```
enterprise-copilot/
├── .env                        # Environment variables (API keys, secrets)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── agents/
│   ├── __init__.py
│   ├── state.py                # LangGraph AgentState TypedDict
│   ├── router_agent.py         # Main router + LangGraph graph
│   ├── hr_agent.py             # HR ReAct agent
│   ├── it_agent.py             # IT ReAct agent
│   ├── finance_agent.py        # Finance ReAct agent
│   └── approval_agent.py       # Approval lifecycle manager
│
├── api/
│   ├── __init__.py
│   └── main.py                 # FastAPI application + all endpoints
│
├── db/
│   ├── __init__.py
│   ├── database.py             # SQLAlchemy engine + session
│   ├── models.py               # ORM models (User, Leave, Ticket, etc.)
│   └── crud.py                 # All database operations + seed data
│
├── docs/
│   ├── hr_policy.txt           # HR policy document (ingested into RAG)
│   ├── it_sop.txt              # IT SOP document (ingested into RAG)
│   └── finance_rules.txt       # Finance policy document (ingested into RAG)
│
├── frontend/
│   └── app.py                  # Streamlit UI
│
├── mcp_server/
│   ├── __init__.py
│   └── server.py               # FastMCP server exposing tools externally
│
├── middleware/
│   ├── __init__.py
│   └── auth.py                 # JWT auth + RBAC middleware
│
├── rag/
│   ├── __init__.py
│   ├── ingest.py               # Document ingestion pipeline
│   └── retriever.py            # RBAC-aware ChromaDB retriever
│
├── tests/
│   └── test_tools.py           # Pytest tests (in-memory SQLite)
│
└── tools/
    ├── __init__.py
    ├── hr_tools.py             # Leave + HR policy tools
    ├── it_tools.py             # Ticket + asset + outage tools
    ├── finance_tools.py        # Payslip + reimbursement + tax tools
    └── email_tools.py          # Email via Power Automate
```

---

## ✅ Prerequisites

Before installing, ensure you have:

- **Python 3.10 or 3.11** (recommended — not 3.12+ due to some LangChain deps)
  - Check: `python --version`
- **pip** updated to latest:
  ```
  python -m pip install --upgrade pip
  ```
- **Git** (optional, for cloning)
- **OpenAI API Key** — https://platform.openai.com/api-keys

---

## 💿 Installation

### Step 1 — Navigate to the project folder

```powershell
cd "C:\Users\Rihan.Muhammad\Desktop\Nexus\enterprise-copilot"
```

### Step 2 — Create a virtual environment

```powershell
python -m venv venv
```

### Step 3 — Activate the virtual environment

```powershell
venv\Scripts\activate
```

> You should see `(venv)` prefix in your terminal.

### Step 4 — Upgrade pip

```powershell
python -m pip install --upgrade pip
```

### Step 5 — Install dependencies

```powershell
pip install -r requirements.txt
```

> ⚠️ **If you get a `chroma-hnswlib` build error on Windows**, see the section below before re-running this.

---

## ✅ No C++ Build Tools Required

This project uses **FAISS** (`faiss-cpu`) instead of ChromaDB for the vector database.
`faiss-cpu` ships pre-built Windows wheels — **no Visual C++ Build Tools needed**.

Just run `pip install -r requirements.txt` and it will install without any compilation.

---

## ⚙️ Configuration (.env)

Open the `.env` file in the project root and fill in your values:

```env
# ── Required ──────────────────────────────────────────
OPENAI_API_KEY=sk-...                        # Your OpenAI API key (REQUIRED)
SECRET_KEY=your_random_secret_key_here       # JWT signing secret (change this!)

# ── Optional ──────────────────────────────────────────
LANGCHAIN_API_KEY=ls__...                    # LangSmith tracing key (optional)
LANGCHAIN_TRACING_V2=true                    # Enable LangSmith tracing (optional)
LANGCHAIN_PROJECT=enterprise-copilot         # LangSmith project name

POWER_AUTOMATE_URL=https://...              # Power Automate HTTP trigger URL (for emails)

DATABASE_URL=sqlite:///./enterprise_copilot.db   # SQLite DB path (default is fine)
CHROMA_PERSIST_DIR=./chroma_db                   # ChromaDB storage path (default is fine)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

> 💡 **Minimum required**: Only `OPENAI_API_KEY` is truly required to run the app.
> All other values have sensible defaults.

---

## 🚀 Running the Application

You need **two terminals** open — one for the API, one for the frontend.

### Terminal 1 — Start the FastAPI Backend

```powershell
cd "C:\Users\Rihan.Muhammad\Desktop\Nexus\enterprise-copilot"
venv\Scripts\activate
uvicorn api.main:app --reload --port 8000
```

On first run, the server will automatically:
1. ✅ Create the SQLite database (`enterprise_copilot.db`)
2. ✅ Seed 6 test users with leave balances, tickets, and payslips
3. ✅ Ingest all policy documents from `docs/` into ChromaDB

You should see:
```
INFO:     Application startup complete.
✅ Database seeded successfully!
✅ Ingestion complete! X chunks stored.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

📖 **Interactive API Docs**: http://localhost:8000/docs

---

### Terminal 2 — Start the Streamlit Frontend

```powershell
cd "C:\Users\Rihan.Muhammad\Desktop\Nexus\enterprise-copilot"
venv\Scripts\activate
streamlit run frontend/app.py
```

The app will open at: **http://localhost:8501**

---

### Terminal 3 (Optional) — Start the MCP Tool Server

```powershell
cd "C:\Users\Rihan.Muhammad\Desktop\Nexus\enterprise-copilot"
venv\Scripts\activate
python mcp_server/server.py
```

Runs at: **http://localhost:8001**

---

## 🔑 Test User Credentials

All accounts use the password: **`password123`**

| Employee ID | Name | Role | Department | Access Level |
|------------|------|------|------------|-------------|
| `EMP000` | Admin User | `admin` | IT | Full access to everything |
| `EMP001` | Alice Johnson | `employee` | Engineering | Own HR, IT, Finance data |
| `EMP002` | Bob Smith | `manager` | Engineering | Own data + team approvals |
| `EMP003` | Carol White | `hr_team` | HR | HR + leave management |
| `EMP004` | Dave Brown | `it_team` | IT | IT tickets + assets |
| `EMP005` | Eve Davis | `finance_team` | Finance | Finance + payslips |

---

## 🌐 API Endpoints Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/login` | ❌ No | Login and get JWT token |
| `GET` | `/health` | ❌ No | Health check |
| `POST` | `/chat` | ✅ Yes | Send message to AI copilot |
| `GET` | `/leave/balance` | ✅ Yes | Get your leave balances |
| `POST` | `/leave/apply` | ✅ Yes | Apply for leave |
| `POST` | `/approve/{request_id}` | ✅ Manager+ | Approve or reject a request |
| `GET` | `/tickets/my` | ✅ Yes | Get your IT tickets |
| `GET` | `/tickets/all` | ✅ IT/Admin | Get all IT tickets |
| `POST` | `/reimbursement/submit` | ✅ Yes | Submit a reimbursement claim |
| `GET` | `/admin/users` | ✅ Admin only | List all users |

**Full interactive docs**: http://localhost:8000/docs

### Example: Login via curl
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "EMP001", "password": "password123"}'
```

### Example: Chat via curl
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"message": "What is my leave balance?", "session_id": "s1"}'
```

---

## 💬 Using the Streamlit Frontend

1. Open **http://localhost:8501** in your browser
2. Enter `EMP001` as Employee ID and `password123` as Password
3. Click **Sign In**

### What you can do:

| Quick Action | What it does |
|-------------|-------------|
| 📊 Leave Balance | Instantly shows your leave balances |
| ✈️ Apply Leave | Opens form to submit a leave request |
| 🎫 Raise IT Ticket | Opens form to create a support ticket |
| 💰 Submit Expense | Opens form for reimbursement claim |
| 📋 HR Policy | Ask any HR policy question |
| 📜 My IT Tickets | Lists all your tickets |
| 💸 My Payslip | Shows latest payslip |

### Example chat questions to try:
- *"What is my casual leave balance?"*
- *"Apply for sick leave from 2025-05-10 to 2025-05-12. Reason: Fever."*
- *"I can't connect to VPN, please raise a ticket."*
- *"Show me my latest payslip."*
- *"What is the notice period policy?"*
- *"Submit a travel reimbursement of ₹2000 for client visit."*

### For managers (EMP002 — Bob Smith):
- Click **⚖️ Pending Approvals** in the sidebar to see and approve/reject team requests.

---

## 📄 How to Add New Policy Documents (RAG)

### Adding `.txt` files

1. Drop any `.txt` file into the `docs/` folder
2. Restart the FastAPI server — it will auto-ingest on startup

### Adding `.pdf` files

1. Drop any `.pdf` file into the `docs/` folder
2. Restart the FastAPI server

PDF filenames determine which department can see the document:
- Filename contains `hr` → HR department access
- Filename contains `it` → IT department access
- Filename contains `finance` → Finance department access
- Any other name → Accessible to all roles

### Re-ingest manually (without restarting):

```powershell
cd enterprise-copilot
venv\Scripts\activate
python -c "from rag.ingest import ingest_documents; ingest_documents()"
```

---

## 📧 Setting Up Power Automate for Email Notifications

When leave is approved/rejected, or a ticket is created, the system sends email notifications. This requires a Power Automate flow.

### Steps:

1. Go to **https://make.powerautomate.com**
2. Click **Create** → **Instant cloud flow**
3. Choose trigger: **"When an HTTP request is received"**
4. Add action: **"Send an email (V2)"** using Office 365 Outlook
5. Map fields in the email action:
   - **To**: `@{triggerBody()?['to']}`
   - **Subject**: `@{triggerBody()?['subject']}`
   - **Body**: `@{triggerBody()?['body']}`
6. **Save** the flow
7. Copy the **HTTP POST URL** shown in the trigger card
8. Paste it into `.env`:
   ```
   POWER_AUTOMATE_URL=https://prod-xx.westus.logic.azure.com/...
   ```

> 💡 If `POWER_AUTOMATE_URL` is not set, email notifications are skipped silently — the app still works fine.

---

## 🧪 Running Tests

Tests use an **in-memory SQLite** database — completely isolated from your real data.

```powershell
cd "C:\Users\Rihan.Muhammad\Desktop\Nexus\enterprise-copilot"
venv\Scripts\activate
pytest tests/test_tools.py -v
```

### What is tested:
- ✅ Leave request creation and validation
- ✅ Leave balance initialization and deduction
- ✅ Overlapping leave detection
- ✅ Leave status approval updates
- ✅ IT ticket creation and duplicate detection
- ✅ Known outage creation and retrieval
- ✅ Finance expense limits validation
- ✅ User authentication (correct + wrong password)
- ✅ RBAC role permission enforcement

---

## 🔧 Troubleshooting

### ❌ `chroma-hnswlib` build error

See [Fixing ChromaDB Error](#-fixing-chromadb--chroma-hnswlib-error-on-windows) section above.

---

### ❌ `ModuleNotFoundError: No module named 'agents'`

You must run all commands from **inside** `enterprise-copilot/`:
```powershell
cd "C:\Users\Rihan.Muhammad\Desktop\Nexus\enterprise-copilot"
uvicorn api.main:app --reload --port 8000
```

---

### ❌ `openai.AuthenticationError`

Your `OPENAI_API_KEY` in `.env` is missing or invalid. Get one at:
https://platform.openai.com/api-keys

---

### ❌ `Connection refused` on Streamlit login

The FastAPI server is not running. Start it first:
```powershell
uvicorn api.main:app --reload --port 8000
```

---

### ❌ `Address already in use` on port 8000

Another process is using port 8000. Use a different port:
```powershell
uvicorn api.main:app --reload --port 8080
```

Then update the `API_BASE` in `frontend/app.py` line 8:
```python
API_BASE = "http://localhost:8080"
```

---

### ❌ RAG returns no results

The FAISS index may be missing. Re-ingest:
```powershell
python -c "from rag.ingest import ingest_documents; ingest_documents()"
```
This creates a `faiss_index/` folder in the project root.

---

### ❌ `sentence_transformers` download is slow

The embedding model (`all-MiniLM-L6-v2`) is ~90MB and is downloaded once from HuggingFace on first run. Subsequent runs use the cached version.

---

## 📞 Contact & Support

| Issue Type | Contact |
|-----------|---------|
| HR queries | hr@company.com |
| IT issues | it@company.com |
| Finance queries | finance@company.com |
| App/system issues | admin@company.com |

---

## 📝 License

Internal tool — Enterprise Solutions Pvt. Ltd. All rights reserved.
