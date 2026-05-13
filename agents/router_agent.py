from typing import Literal, TypedDict


IntentType = Literal[
    "small_talk",
    "rag",

    # HR
    "apply_leave",
    "leave_balance",
    "leave_status",
    "pending_leaves",
    "approve_leave",
    "reject_leave",
    "cancel_leave",

    # IT tickets
    "raise_it_ticket",
    "ticket_status",
    "assign_ticket",
    "resolve_ticket",

    # Asset requests
    "request_asset",
    "asset_status",
    "manager_approve_asset",
    "manager_reject_asset",
    "it_approve_asset",
    "it_reject_asset",

    # Finance
    "submit_reimbursement",
    "reimbursement_status",
    "approve_reimbursement",
    "reject_reimbursement",

    # Approvals
    "pending_approvals",

    "unknown",
]


class RouterResult(TypedDict, total=False):
    intent: IntentType
    agent: str
    confidence: float
    reason: str
    request_id: int | None
    ticket_id: int | None
    action: str | None
    target_type: str | None


def normalize_text(text: str) -> str:
    return text.lower().strip()


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


from config import MODEL_PROVIDER, GROQ_API_KEY

def format_chat_history(chat_history):
    return "\n".join(
        f"{item.get('role')}: {item.get('content')}"
        for item in chat_history[-10:]
    )

def detect_intent_with_groq(text: str, chat_history: list = None) -> dict | None:
    try:
        from langchain_groq import ChatGroq
        from langchain_core.prompts import ChatPromptTemplate
        import json
        
        llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=GROQ_API_KEY, temperature=0).bind(response_format={"type": "json_object"})
        
        history_text = format_chat_history(chat_history or [])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an intent router for Workplace Buddy.
You receive:
- current user message
- recent chat history
- user role

Allowed intents:
small_talk, rag, apply_leave, leave_balance, leave_status, pending_leaves, approve_leave, reject_leave, cancel_leave, raise_it_ticket, ticket_status, assign_ticket, resolve_ticket, request_asset, asset_status, manager_approve_asset, manager_reject_asset, it_approve_asset, it_reject_asset, submit_reimbursement, reimbursement_status, approve_reimbursement, reject_reimbursement, pending_approvals, generic_approval

Use chat history to resolve vague follow-up commands.

Examples:

Recent assistant message:
"Pending Leave Requests:
ID 7 | Rifa (EMP001) | casual | 2026-06-10 to 2026-06-10"

Current user:
"Approve the ID 7"

Return JSON:
{{
  "intent": "approve_leave",
  "agent": "hr_agent",
  "request_id": 7,
  "ticket_id": null,
  "action": "approve",
  "target_type": "leave"
}}

Recent assistant message:
"Finance Requests:
- Request 2: EMP003 (travel, $500)"

Current user:
"Approve the ID 2"

Return JSON:
{{
  "intent": "approve_reimbursement",
  "agent": "finance_agent",
  "request_id": 2,
  "ticket_id": null,
  "action": "approve",
  "target_type": "finance"
}}

Recent assistant message:
"Asset Requests:
- Request ID 5: laptop for EMP001"

Current user:
"Approve ID 5"

Return JSON:
{{
  "intent": "manager_approve_asset",
  "agent": "it_agent",
  "request_id": 5,
  "ticket_id": null,
  "action": "approve",
  "target_type": "asset"
}}

Recent assistant message:
"IT Ticket status:
Ticket 3 | laptop | Status: open"

Current user:
"Approve ID 3"

Return JSON:
{{
  "intent": "resolve_ticket",
  "agent": "it_agent",
  "request_id": null,
  "ticket_id": 3,
  "action": "resolve",
  "target_type": "ticket"
}}

If unclear, return:
{{
  "intent": "generic_approval",
  "agent": "approval_agent",
  "request_id": 7,
  "ticket_id": null,
  "action": "approve",
  "target_type": "unknown"
}}

You must return valid JSON."""),
            ("human", "Recent chat history:\n{history_text}\n\nCurrent user:\n{text}")
        ])
        
        chain = prompt | llm
        response_text = chain.invoke({"text": text, "history_text": history_text}).content.strip()
        data = json.loads(response_text)
        print(f"\n[GROQ ROUTER JSON] {data}\n")
        return data
    except Exception as e:
        print(f"Groq intent detection failed: {e}")
    return None


def detect_intent(user_input: str, chat_history: list = None) -> RouterResult:
    """
    Detects user intent and maps it to the correct agent.
    """

    chat_history = chat_history or []
    text = normalize_text(user_input)

    if not text:
        return {
            "intent": "unknown",
            "agent": "unknown_agent",
            "confidence": 0.0,
            "reason": "Empty user input."
        }
        
    if MODEL_PROVIDER.lower() == "groq" and GROQ_API_KEY:
        llm_result = detect_intent_with_groq(text, chat_history)
        if llm_result and "intent" in llm_result:
            intent = llm_result.get("intent", "unknown")
            valid_intents = [
                "small_talk", "rag", "apply_leave", "leave_balance", "leave_status",
                "pending_leaves", "approve_leave", "reject_leave", "cancel_leave",
                "raise_it_ticket", "ticket_status", "assign_ticket", "resolve_ticket",
                "request_asset", "asset_status", "manager_approve_asset",
                "manager_reject_asset", "it_approve_asset", "it_reject_asset",
                "submit_reimbursement", "reimbursement_status", "approve_reimbursement",
                "reject_reimbursement", "pending_approvals", "generic_approval"
            ]
            
            if intent in valid_intents:
                return {
                    "intent": intent,
                    "agent": route_to_agent(intent),
                    "confidence": 0.9,
                    "reason": "LLM classification",
                    "request_id": llm_result.get("request_id"),
                    "ticket_id": llm_result.get("ticket_id"),
                    "action": llm_result.get("action"),
                    "target_type": llm_result.get("target_type")
                }

    # Small talk
    if text in ["hi", "hello", "hey", "good morning", "good evening", "good afternoon"]:
        return {
            "intent": "small_talk",
            "agent": "small_talk_agent",
            "confidence": 0.95,
            "reason": "Greeting detected."
        }

    if contains_any(text, ["thank you", "thanks", "bye", "goodbye"]):
        return {
            "intent": "small_talk",
            "agent": "small_talk_agent",
            "confidence": 0.9,
            "reason": "Small talk phrase detected."
        }

    # Approval / rejection intents must come before general status checks
    if contains_any(text, ["approve leave", "approve my leave", "approve request"]) and "leave" in text:
        return {
            "intent": "approve_leave",
            "agent": "hr_agent",
            "confidence": 0.9,
            "reason": "Leave approval intent detected."
        }

    if contains_any(text, ["reject leave", "reject my leave"]) or ("reject" in text and "leave" in text):
        return {
            "intent": "reject_leave",
            "agent": "hr_agent",
            "confidence": 0.9,
            "reason": "Leave rejection intent detected."
        }

    if contains_any(text, ["pending leaves", "pending leave requests", "show leave requests"]):
        return {
            "intent": "pending_leaves",
            "agent": "hr_agent",
            "confidence": 0.9,
            "reason": "Pending leave list intent detected."
        }

    # Leave balance and status
    if contains_any(text, ["leave balance", "my leaves", "remaining leaves", "available leaves"]):
        return {
            "intent": "leave_balance",
            "agent": "hr_agent",
            "confidence": 0.9,
            "reason": "Leave balance intent detected."
        }

    if contains_any(text, ["leave status", "leave request status", "status of my leave", "check my leave"]):
        return {
            "intent": "leave_status",
            "agent": "hr_agent",
            "confidence": 0.9,
            "reason": "Leave status intent detected."
        }

    if contains_any(text, ["cancel leave", "cancel my leave"]):
        return {
            "intent": "cancel_leave",
            "agent": "hr_agent",
            "confidence": 0.9,
            "reason": "Cancel leave intent detected."
        }

    # Apply leave
    # Important: We avoid classifying policy questions like
    # "Can I take maternity leave?" as apply_leave.
    policy_question_patterns = [
        "what is",
        "explain",
        "how many",
        "allowed",
        "policy",
        "rules",
        "can i take maternity",
        "maternity leave",
        "notice period",
        "work from home",
        "wfh"
    ]

    if "leave" in text and contains_any(text, ["apply", "request", "take", "need leave"]):
        if contains_any(text, policy_question_patterns):
            return {
                "intent": "rag",
                "agent": "rag_agent",
                "confidence": 0.85,
                "reason": "Leave-related policy question detected."
            }

        return {
            "intent": "apply_leave",
            "agent": "hr_agent",
            "confidence": 0.9,
            "reason": "Apply leave intent detected."
        }

    # IT ticket approvals/actions
    if contains_any(text, ["assign ticket", "assign it ticket"]):
        return {
            "intent": "assign_ticket",
            "agent": "it_agent",
            "confidence": 0.9,
            "reason": "Assign ticket intent detected."
        }

    if contains_any(text, ["resolve ticket", "close ticket", "mark ticket resolved"]):
        return {
            "intent": "resolve_ticket",
            "agent": "it_agent",
            "confidence": 0.9,
            "reason": "Resolve ticket intent detected."
        }

    if contains_any(text, ["ticket status", "my ticket", "show tickets", "show all tickets", "show all it tickets", "it ticket status"]):
        return {
            "intent": "ticket_status",
            "agent": "it_agent",
            "confidence": 0.9,
            "reason": "Ticket status intent detected."
        }

    if contains_any(
        text,
        [
            "laptop issue",
            "vpn not working",
            "outlook not working",
            "email not working",
            "printer issue",
            "network issue",
            "software install",
            "software installation",
            "raise ticket",
            "create ticket",
            "it issue"
        ]
    ):
        return {
            "intent": "raise_it_ticket",
            "agent": "it_agent",
            "confidence": 0.9,
            "reason": "IT ticket creation intent detected."
        }

    # Asset requests
    if contains_any(text, ["manager approve asset", "approve asset as manager"]):
        return {
            "intent": "manager_approve_asset",
            "agent": "it_agent",
            "confidence": 0.9,
            "reason": "Manager asset approval intent detected."
        }

    if contains_any(text, ["manager reject asset", "reject asset as manager"]):
        return {
            "intent": "manager_reject_asset",
            "agent": "it_agent",
            "confidence": 0.9,
            "reason": "Manager asset rejection intent detected."
        }

    if contains_any(text, ["it approve asset", "approve asset as it"]):
        return {
            "intent": "it_approve_asset",
            "agent": "it_agent",
            "confidence": 0.9,
            "reason": "IT asset approval intent detected."
        }

    if contains_any(text, ["it reject asset", "reject asset as it"]):
        return {
            "intent": "it_reject_asset",
            "agent": "it_agent",
            "confidence": 0.9,
            "reason": "IT asset rejection intent detected."
        }

    if contains_any(text, ["asset status", "asset request status", "show asset requests"]):
        return {
            "intent": "asset_status",
            "agent": "it_agent",
            "confidence": 0.9,
            "reason": "Asset status intent detected."
        }

    if contains_any(text, ["request asset", "need laptop", "need a laptop", "need monitor", "need keyboard", "need mouse", "need vpn token", "need software license", "request laptop", "request a laptop", "request for a laptop", "request for laptop", "request monitor", "request keyboard", "request mouse"]):
        return {
            "intent": "request_asset",
            "agent": "it_agent",
            "confidence": 0.9,
            "reason": "Asset request intent detected."
        }

    # Finance
    if contains_any(text, ["approve reimbursement", "approve claim"]):
        return {
            "intent": "approve_reimbursement",
            "agent": "finance_agent",
            "confidence": 0.9,
            "reason": "Reimbursement approval intent detected."
        }

    if contains_any(text, ["reject reimbursement", "reject claim"]):
        return {
            "intent": "reject_reimbursement",
            "agent": "finance_agent",
            "confidence": 0.9,
            "reason": "Reimbursement rejection intent detected."
        }

    if contains_any(text, ["reimbursement status", "claim status", "expense status"]):
        return {
            "intent": "reimbursement_status",
            "agent": "finance_agent",
            "confidence": 0.9,
            "reason": "Reimbursement status intent detected."
        }

    if contains_any(text, ["submit reimbursement", "travel claim", "internet bill", "food expense", "client meeting claim", "expense claim"]):
        return {
            "intent": "submit_reimbursement",
            "agent": "finance_agent",
            "confidence": 0.9,
            "reason": "Submit reimbursement intent detected."
        }

    # General policy / RAG questions
    if contains_any(
        text,
        [
            "policy",
            "rule",
            "rules",
            "notice period",
            "casual leaves",
            "sick leaves",
            "maternity",
            "work from home",
            "wfh",
            "reimbursement policy",
            "asset flow",
            "approval flow"
        ]
    ):
        return {
            "intent": "rag",
            "agent": "rag_agent",
            "confidence": 0.85,
            "reason": "Policy/RAG question detected."
        }

    # Deterministic fallback for pending_approvals
    if contains_any(text, ["pending approval", "pending approvals", "approval requests", "approvals waiting", "requests pending approval"]):
        return {
            "intent": "pending_approvals",
            "agent": "approval_agent",
            "confidence": 0.9,
            "reason": "Pending approvals fallback detected."
        }

    # Deterministic fallback for follow-up approval phrases
    import re
    match = re.search(r"(approve|reject|resolve).*(?:id|request|ticket)\s*(\d+)", text)
    if match or contains_any(text, ["approve request", "approve ticket", "reject request", "reject ticket", "approve", "reject", "resolve"]):
        history_text_lower = format_chat_history(chat_history).lower()
        combined_text = history_text_lower + "\n" + text

        has_finance = "finance request" in combined_text or "reimbursement" in combined_text
        has_leave = "leave request" in combined_text or "pending leave" in combined_text
        has_asset = "asset request" in combined_text
        has_ticket = "it ticket" in combined_text or "ticket" in combined_text

        categories_found = sum([has_finance, has_leave, has_asset, has_ticket])
        is_approve = "approve" in text

        request_id = None
        if match:
            request_id = int(match.group(2))

        if categories_found == 1:
            if has_finance:
                return {"intent": "approve_reimbursement" if is_approve else "reject_reimbursement", "agent": "finance_agent", "confidence": 0.85, "reason": "Follow-up finance approval.", "request_id": request_id}
            if has_leave:
                return {"intent": "approve_leave" if is_approve else "reject_leave", "agent": "hr_agent", "confidence": 0.85, "reason": "Follow-up leave approval.", "request_id": request_id}
            if has_asset:
                return {"intent": "manager_approve_asset" if is_approve else "manager_reject_asset", "agent": "it_agent", "confidence": 0.85, "reason": "Follow-up asset approval.", "request_id": request_id}
            if has_ticket and (is_approve or "resolve" in text):
                return {"intent": "resolve_ticket", "agent": "it_agent", "confidence": 0.85, "reason": "Follow-up ticket resolution.", "ticket_id": request_id}
        elif categories_found > 1 or categories_found == 0:
            return {"intent": "generic_approval", "agent": "approval_agent", "confidence": 0.85, "reason": "Clarification needed.", "request_id": request_id}

    return {
        "intent": "unknown",
        "agent": "unknown_agent",
        "confidence": 0.3,
        "reason": "No matching intent found."
    }


def route_to_agent(intent: IntentType) -> str:
    """
    Maps intent to agent name.
    """

    if intent in [
        "apply_leave",
        "leave_balance",
        "leave_status",
        "pending_leaves",
        "approve_leave",
        "reject_leave",
        "cancel_leave"
    ]:
        return "hr_agent"

    if intent in [
        "raise_it_ticket",
        "ticket_status",
        "assign_ticket",
        "resolve_ticket",
        "request_asset",
        "asset_status",
        "manager_approve_asset",
        "manager_reject_asset",
        "it_approve_asset",
        "it_reject_asset"
    ]:
        return "it_agent"

    if intent in [
        "submit_reimbursement",
        "reimbursement_status",
        "approve_reimbursement",
        "reject_reimbursement"
    ]:
        return "finance_agent"

    if intent == "rag":
        return "rag_agent"

    if intent == "small_talk":
        return "small_talk_agent"

    if intent == "pending_approvals":
        return "approval_agent"

    if intent == "generic_approval":
        return "approval_agent"

    return "unknown_agent"