# Enterprise Multi-Agent AI Copilot — Agent Flow

This document describes the complete request lifecycle from the moment a user types a message to the moment a response is returned.

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User (Browser)                         │
│                  Streamlit  :8501                            │
└────────────────────────────┬────────────────────────────────┘
                             │  HTTP POST /chat
                             │  Header: X-Employee-ID
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend  :8000                      │
│                                                             │
│   Auth Middleware → /chat endpoint → run_graph()            │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              LangGraph Router Graph                         │
│                                                             │
│  detect_intent ──► validate_role ──► [domain agent]        │
│                                           │                 │
│                                     format_response         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Step-by-Step Request Flow

```mermaid
flowchart TD
    A([User types message in Streamlit]) --> B

    B[/"POST /chat\nHeader: X-Employee-ID"/] --> C

    C{Auth Middleware\nmiddleware/auth.py} -->|Employee not found| ERR1([HTTP 404])
    C -->|Valid user| D

    D[Build AgentState\nuser_id, user_role, user_name,\nuser_department, user_email,\nmessages] --> E

    E([LangGraph Graph START]) --> F

    subgraph LangGraph Router Graph
        F["detect_intent node\nrouter_agent.py"]
        F -->|"Calls Groq LLM\nwith router.txt prompt"| G
        G["Intent classified\nhr_policy / hr_leave /\nit_ticket / it_asset /\nfinance_payslip / finance_reimbursement /\nfinance_tax / unknown"] --> H

        H["validate_role node\nChecks ROLE_INTENT_MAP"] -->|"Role not allowed\nfor this intent"| I
        H -->|Role allowed| J

        I["state.error = access_denied\nstate.final_response = 'Access denied'"] --> R

        J{Route by intent} -->|hr_policy\nhr_leave| K
        J -->|it_ticket\nit_asset| L
        J -->|finance_*| M
        J -->|unknown| R

        subgraph HR Agent - hr_agent.py
            K["Inject hr.txt prompt\n+ user context into message"] --> K2
            K2["create_react_agent\nGroq LLM + HR Tools"] --> K3
            K3{Tool calls?}
            K3 -->|get_leave_balance| T1([DB: leave_balance table])
            K3 -->|apply_leave| T2([DB: leave_requests table])
            K3 -->|get_leave_history| T3([DB: leave_requests table])
            K3 -->|cancel_leave| T4([DB: leave_requests table])
            K3 -->|get_pending_leave_approvals| T5([DB: leave_requests table])
            K3 -->|approve_or_reject_leave| T6([DB: leave_requests table])
            K3 -->|query_hr_policy| T7([FAISS Vector Index\nhr_policy.txt])
            K3 -->|Done| K4[state.final_response set]
        end

        subgraph IT Agent - it_agent.py
            L["Inject it.txt prompt\n+ user context into message"] --> L2
            L2["create_react_agent\nGroq LLM + IT Tools"] --> L3
            L3{Tool calls?}
            L3 -->|create_ticket| U1([DB: it_tickets table])
            L3 -->|get_ticket_status| U2([DB: it_tickets table])
            L3 -->|get_my_tickets| U3([DB: it_tickets table])
            L3 -->|get_all_tickets| U4([DB: it_tickets table])
            L3 -->|assign_ticket| U5([DB: it_tickets table])
            L3 -->|resolve_ticket| U6([DB: it_tickets table])
            L3 -->|request_asset| U7([DB: asset_requests table])
            L3 -->|check_known_outages| U8([DB: outages table])
            L3 -->|Done| L4[state.final_response set]
        end

        subgraph Finance Agent - finance_agent.py
            M["Inject finance.txt prompt\n+ user context into message"] --> M2
            M2["create_react_agent\nGroq LLM + Finance Tools"] --> M3
            M3{Tool calls?}
            M3 -->|get_latest_payslip| V1([DB: payslips table])
            M3 -->|submit_reimbursement| V2([DB: reimbursements table])
            M3 -->|get_reimbursement_status| V3([DB: reimbursements table])
            M3 -->|get_tax_info| V4([DB: tax_info table])
            M3 -->|Done| M4[state.final_response set]
        end

        K4 --> R
        L4 --> R
        M4 --> R

        R["format_response node\nReturns final_response or\ndefault fallback message"]
    end

    R --> S([LangGraph Graph END])
    S --> Z[/"FastAPI returns\nChatResponse JSON"/]
    Z --> ZZ([Streamlit renders\nresponse in chat])
```

---

## 3. Context Injection Pattern (All Domain Agents)

Each domain agent prepends a **context block** to the user's first message before passing it to the ReAct agent. This eliminates the need for SystemMessage (which causes issues on some LLM providers):

```
Instructions: <contents of agents/prompts/{agent}.txt>
User ID: 3, Name: Alice Johnson, Role: employee, Dept: Engineering.
IMPORTANT: Whenever a tool requires 'user_id', you MUST use the exact integer 3.

<original user message>
```

---

## 4. Prompt Files (agents/prompts/)

| File | Used by | Purpose |
|------|---------|---------|
| `hr.txt` | `hr_agent.py` | HR assistant persona and responsibilities |
| `it.txt` | `it_agent.py` | IT support assistant persona and responsibilities |
| `finance.txt` | `finance_agent.py` | Finance assistant persona and responsibilities |
| `router.txt` | `router_agent.py` | Intent classification instructions with `{intent_labels}` and `{user_message}` placeholders |

> **To update any agent's behaviour, edit only the `.txt` file. No Python changes needed.**

---

## 5. Role-Based Access Control (RBAC)

The `validate_role` node enforces which intents each role can access:

| Role | Allowed Intents |
|------|----------------|
| `employee` | hr_policy, hr_leave, it_ticket, it_asset, finance_payslip, finance_reimbursement, finance_tax |
| `manager` | All employee intents |
| `hr_team` | hr_policy, hr_leave, it_ticket, finance_payslip, finance_reimbursement |
| `it_team` | it_ticket, it_asset, hr_policy |
| `finance_team` | finance_payslip, finance_reimbursement, finance_tax, hr_policy |
| `admin` | All intents |

---

## 6. RAG (Retrieval-Augmented Generation) Flow

Used only when `query_hr_policy` tool is called by the HR agent:

```
User question
     │
     ▼
HuggingFace Embeddings (all-MiniLM-L6-v2)
     │
     ▼
FAISS similarity_search (faiss_index/)
     │
     ▼
RBAC filter — only chunks the user's role can access
     │
     ▼
Department filter — only HR chunks (when called from hr_agent)
     │
     ▼
Top-k chunks returned as formatted context string
     │
     ▼
Included in LLM tool response → final answer with source citations
```

Source documents ingested into FAISS (`docs/`):

| File | Department | Accessible to |
|------|-----------|--------------|
| `hr_policy.txt` | HR | employee, manager, hr_team, admin |
| `it_sop.txt` | IT | employee, manager, it_team, admin |
| `finance_rules.txt` | Finance | employee, manager, finance_team, admin |

---

## 7. Approval Flow

When an agent action requires approval (e.g. leave > 3 days, asset request):

```
Agent sets requires_approval = True
        │
        ▼
ApprovalManager.create_pending_approval()
(in-memory registry: agents/approval_agent.py)
        │
        ▼
Frontend shows "Approval Required" warning banner
        │
        ▼
Manager logs in → Pending Approvals page → Approve / Reject
        │
        ▼
POST /approve/{id} → approval_manager.process_approval()
        │
        ├── Updates DB (leave / asset / reimbursement status)
        └── Sends email notification via Power Automate (if configured)
```

---

## 8. File Structure Reference

```
enterprise-copilot/
├── api/
│   └── main.py              ← FastAPI app, all HTTP endpoints
├── agents/
│   ├── router_agent.py      ← LangGraph graph: detect_intent → validate_role → route
│   ├── hr_agent.py          ← HR ReAct agent
│   ├── it_agent.py          ← IT ReAct agent
│   ├── finance_agent.py     ← Finance ReAct agent
│   ├── approval_agent.py    ← In-memory approval registry
│   ├── state.py             ← AgentState TypedDict (shared graph state)
│   └── prompts/
│       ├── __init__.py      ← Loads .txt files, exports constants
│       ├── hr.txt           ← HR agent system prompt (edit freely)
│       ├── it.txt           ← IT agent system prompt (edit freely)
│       ├── finance.txt      ← Finance agent system prompt (edit freely)
│       └── router.txt       ← Intent classification prompt (edit freely)
├── tools/
│   ├── hr_tools.py          ← LangChain tools: leave management
│   ├── it_tools.py          ← LangChain tools: ticket & asset management
│   ├── finance_tools.py     ← LangChain tools: payslip, reimbursement, tax
│   └── email_tools.py       ← Power Automate email notifications
├── rag/
│   ├── ingest.py            ← Load docs → chunk → embed → save FAISS index
│   └── retriever.py         ← RBAC-aware FAISS similarity search
├── db/
│   ├── models.py            ← SQLAlchemy ORM models
│   ├── crud.py              ← All DB read/write operations
│   └── database.py          ← SQLite engine + session factory
├── middleware/
│   └── auth.py              ← X-Employee-ID header auth + require_role() RBAC
├── frontend/
│   └── app.py               ← Streamlit UI
└── docs/
    ├── agent_flow.md        ← This file
    ├── hr_policy.txt        ← RAG source document
    ├── it_sop.txt           ← RAG source document
    └── finance_rules.txt    ← RAG source document
```
