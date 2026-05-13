# Enterprise Multi-Agent AI Copilot

This project is an internal enterprise AI assistant for HR, IT, and Finance operations.

## Main Features

- HR policy assistant using RAG
- Leave management workflow
- IT support ticket workflow
- Asset request workflow
- Basic finance reimbursement workflow
- Role Based Access Control
- LangGraph based routing
- SQLite database
- Memory and logs
- Power Automate email integration
- FastMCP tool exposure
- Streamlit user interface

## Tech Stack

- Python
- LangChain
- LangGraph
- ChromaDB
- SQLite
- Streamlit
- FastMCP
- Power Automate

## FastMCP Integration

Workplace Buddy exposes important backend workflows through FastMCP.

Exposed MCP tools include:

- get_leave_balance_mcp
- apply_leave_mcp
- approve_leave_mcp
- create_it_ticket_mcp
- get_ticket_status_mcp
- request_asset_mcp
- manager_approve_asset_mcp
- it_approve_asset_mcp
- submit_reimbursement_mcp
- approve_reimbursement_mcp
- ask_policy_question_mcp

These tools wrap the same backend functions used by the LangGraph workflow. This shows that Workplace Buddy can expose enterprise operations as MCP-compatible tools for external AI clients or agent systems.