"""
Streamlit frontend for the Enterprise Multi-Agent AI Copilot.
"""
import datetime
import httpx
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="Enterprise AI Copilot", page_icon="🤖", layout="wide")

# ── Session State Init ────────────────────────
for key, default in [
    ("employee_id", "EMP001"), ("user_info", None), ("chat_history", []),
    ("current_page", "chat"), ("session_id", f"s_{datetime.datetime.utcnow().timestamp()}"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── CSS ───────────────────────────────────────
st.markdown("""
<style>
.stApp{background:#0f1117}
.chat-user{background:linear-gradient(135deg,#667eea,#764ba2);color:white;
  border-radius:18px 18px 4px 18px;padding:12px 16px;margin:6px 0;
  max-width:75%;margin-left:auto;font-size:14px}
.chat-bot{background:#1e2130;color:#e2e8f0;border:1px solid #2d3748;
  border-radius:18px 18px 18px 4px;padding:12px 16px;margin:6px 0;
  max-width:85%;font-size:14px}
.approval-warn{background:#2d2006;border:1px solid #f6ad55;border-radius:8px;
  padding:10px 14px;color:#f6ad55;font-size:13px;margin-top:6px}
.user-card{background:linear-gradient(135deg,#1a1f35,#252d45);
  border-radius:12px;padding:16px;margin-bottom:16px;border:1px solid #2d3748}
.stButton>button{width:100%;border-radius:8px;
  background:linear-gradient(135deg,#667eea,#764ba2);
  color:white;border:none;font-weight:500}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────
def auth_headers():
    return {"X-Employee-ID": st.session_state.employee_id}

def api_post(path, body=None):
    try:
        r = httpx.post(f"{API_BASE}{path}", json=body or {}, headers=auth_headers(), timeout=60)
        return {"ok": r.status_code == 200, "data": r.json(), "status": r.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def api_get(path):
    try:
        r = httpx.get(f"{API_BASE}{path}", headers=auth_headers(), timeout=30)
        return {"ok": r.status_code == 200, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def add_msg(role, content, requires_approval=False):
    st.session_state.chat_history.append({
        "role": role, "content": content,
        "requires_approval": requires_approval,
        "time": datetime.datetime.now().strftime("%H:%M"),
    })

def send_chat(message):
    if not message.strip():
        return
    add_msg("user", message)
    with st.spinner("🤔 Thinking..."):
        res = api_post("/chat", {"message": message, "session_id": st.session_state.session_id})
    if res["ok"]:
        d = res["data"]
        add_msg("assistant", d.get("response", ""), d.get("requires_approval", False))
    else:
        add_msg("assistant", f"❌ Error: {res.get('error', res.get('data', ''))}")
    st.rerun()


# ── Sidebar ───────────────────────────────────
def render_sidebar():
    role_map = {
        "Employee": "EMP001",
        "Manager": "EMP002",
        "HR Team": "EMP003",
        "IT Team": "EMP004",
        "Finance Team": "EMP005",
        "Admin": "EMP000"
    }
    
    current_index = 0
    for i, emp_id in enumerate(role_map.values()):
        if emp_id == st.session_state.employee_id:
            current_index = i
            break
            
    selected_role = st.selectbox("🎭 Simulate Role", list(role_map.keys()), index=current_index)
    
    if role_map[selected_role] != st.session_state.employee_id:
        st.session_state.employee_id = role_map[selected_role]
        st.session_state.user_info = None
        st.session_state.chat_history = []
        st.session_state.current_page = "chat"
        st.rerun()

    u = st.session_state.user_info
    if u:
        st.markdown(f"""
        <div class='user-card'>
          <h3 style='margin:0;color:#e2e8f0'>👤 {u['name']}</h3>
          <p style='margin:4px 0;color:#a0aec0;font-size:13px'>
            🎫 {u['employee_id']} &nbsp;|&nbsp; 🏷️ {u['role'].replace('_',' ').title()}</p>
          <p style='margin:0;color:#718096;font-size:12px'>🏢 {u['department']}</p>
        </div>""", unsafe_allow_html=True)

        st.markdown("### ⚡ Quick Actions")
        actions = [
            ("📊 Leave Balance",    lambda: send_chat("What is my leave balance?")),
            ("✈️ Apply Leave",      lambda: setpage("apply_leave")),
            ("🎫 Raise IT Ticket",  lambda: setpage("it_ticket")),
            ("💰 Submit Expense",   lambda: setpage("reimbursement")),
            ("📋 HR Policy",        lambda: setpage("hr_policy")),
            ("📜 My IT Tickets",    lambda: send_chat("Show me my IT tickets.")),
            ("💸 My Payslip",       lambda: send_chat("Show me my latest payslip.")),
        ]
        for label, action in actions:
            if st.button(label):
                action()

        if u["role"] in ("manager", "hr_team", "it_team", "finance_team", "admin"):
            st.markdown("---")
            if st.button("⚖️ Pending Approvals", type="primary"):
                setpage("approvals")

        st.markdown("---")
        if st.button("💬 Chat"):
            setpage("chat")


def setpage(p):
    st.session_state.current_page = p
    st.rerun()


# ── Chat Page ─────────────────────────────────
def render_chat():
    st.markdown("## 💬 Enterprise AI Copilot")
    st.markdown("*Ask anything about HR policies, IT support, or finance!*")
    st.markdown("---")

    if not st.session_state.chat_history:
        st.markdown("""<div style='text-align:center;padding:40px;color:#4a5568'>
          <h3>👋 How can I help you today?</h3>
          <p>Try: leave balance · IT ticket · payslip · HR policy</p>
        </div>""", unsafe_allow_html=True)
    else:
        for msg in st.session_state.chat_history:
            t = msg["time"]
            if msg["role"] == "user":
                st.markdown(f"<div class='chat-user'><b>You</b> · {t}<br>{msg['content']}</div>",
                            unsafe_allow_html=True)
            else:
                html = msg["content"].replace("\n", "<br>")
                st.markdown(f"<div class='chat-bot'><b>🤖 Copilot</b> · {t}<br>{html}</div>",
                            unsafe_allow_html=True)
                if msg.get("requires_approval"):
                    st.markdown("<div class='approval-warn'>⏳ <b>Approval Required</b>: Sent to your manager.</div>",
                                unsafe_allow_html=True)

    st.markdown("---")
    with st.form("chat_form", clear_on_submit=True):
        c1, c2 = st.columns([5, 1])
        with c1:
            msg = st.text_input("Message", placeholder="e.g. What is my leave balance?", label_visibility="collapsed")
        with c2:
            if st.form_submit_button("Send ▶", use_container_width=True) and msg:
                send_chat(msg)


# ── Forms ─────────────────────────────────────
def render_apply_leave():
    st.markdown("## ✈️ Apply for Leave")
    with st.form("leave_form"):
        lt = st.selectbox("Leave Type", ["casual", "sick", "annual", "maternity", "paternity"])
        c1, c2 = st.columns(2)
        s = c1.date_input("Start Date", min_value=datetime.date.today())
        e = c2.date_input("End Date", min_value=datetime.date.today())
        reason = st.text_area("Reason")
        if st.form_submit_button("📤 Submit", use_container_width=True):
            send_chat(f"Apply for {lt} leave from {s} to {e}. Reason: {reason}")
            setpage("chat")
    if st.button("← Back"): setpage("chat")


def render_it_ticket():
    st.markdown("## 🎫 Raise an IT Ticket")
    with st.form("ticket_form"):
        it = st.selectbox("Issue Type", ["vpn", "laptop", "email", "printer", "network", "software"])
        title = st.text_input("Title", placeholder="Short description")
        desc = st.text_area("Description", placeholder="Details...")
        pri = st.selectbox("Priority", ["low", "medium", "high", "critical"])
        if st.form_submit_button("🎫 Submit", use_container_width=True):
            send_chat(f"Create an IT ticket. Type: {it}. Title: {title}. Description: {desc}. Priority: {pri}.")
            setpage("chat")
    if st.button("← Back"): setpage("chat")


def render_reimbursement():
    st.markdown("## 💰 Submit Reimbursement")
    with st.form("reimb_form"):
        et = st.selectbox("Expense Type", ["travel", "internet", "food", "client_meeting"])
        amt = st.number_input("Amount (INR ₹)", min_value=0.0, step=10.0)
        desc = st.text_area("Description")
        if st.form_submit_button("💸 Submit", use_container_width=True):
            send_chat(f"Submit reimbursement. Type: {et}. Amount: ₹{amt}. Description: {desc}.")
            setpage("chat")
    if st.button("← Back"): setpage("chat")


def render_hr_policy():
    st.markdown("## 📋 HR Policy Q&A")
    with st.form("policy_form"):
        q = st.text_area("Your question", placeholder="e.g. What is the notice period for managers?")
        if st.form_submit_button("🔍 Search", use_container_width=True) and q:
            send_chat(q)
            setpage("chat")
    if st.button("← Back"): setpage("chat")


def render_approvals():
    st.markdown("## ⚖️ Pending Approvals")
    try:
        import sys, os as _os
        sys.path.insert(0, _os.path.dirname(_os.path.dirname(__file__)))
        from agents.approval_agent import approval_manager as am
        pending = am.get_pending_approvals(st.session_state.user_info["id"])
    except Exception:
        pending = []

    if not pending:
        st.info("✅ No pending approvals.")
    else:
        for appr in pending:
            with st.expander(f"#{appr['approval_id']} — {appr['request_type'].title()} (Employee #{appr['employee_id']})"):
                st.json(appr)
                comment = st.text_input("Comment", key=f"c_{appr['approval_id']}")
                col1, col2 = st.columns(2)
                if col1.button("✅ Approve", key=f"a_{appr['approval_id']}"):
                    r = api_post(f"/approve/{appr['approval_id']}", {"decision": "approved", "comment": comment or "Approved"})
                    st.success("Approved!") if r["ok"] else st.error(r.get("data"))
                    st.rerun()
                if col2.button("❌ Reject", key=f"r_{appr['approval_id']}"):
                    r = api_post(f"/approve/{appr['approval_id']}", {"decision": "rejected", "comment": comment or "Rejected"})
                    st.success("Rejected.") if r["ok"] else st.error(r.get("data"))
                    st.rerun()
    if st.button("← Back"): setpage("chat")


# ── Main ──────────────────────────────────────
def main():
    # Fetch user info if missing
    if st.session_state.user_info is None:
        r = api_get("/auth/me")
        if r["ok"]:
            st.session_state.user_info = r["data"]
        else:
            st.error(f"Cannot connect to server. Error: {r.get('error', 'unknown')}")
            return

    with st.sidebar:
        render_sidebar()
        
    pages = {
        "chat": render_chat,
        "apply_leave": render_apply_leave,
        "it_ticket": render_it_ticket,
        "reimbursement": render_reimbursement,
        "hr_policy": render_hr_policy,
        "approvals": render_approvals,
    }
    pages.get(st.session_state.current_page, render_chat)()


if __name__ == "__main__":
    main()
