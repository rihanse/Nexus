const userSelect = document.getElementById("userSelect");
const employeeId = document.getElementById("employeeId");
const employeeRole = document.getElementById("employeeRole");
const employeeDepartment = document.getElementById("employeeDepartment");

const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

const lastIntent = document.getElementById("lastIntent");
const lastAgent = document.getElementById("lastAgent");
const lastTool = document.getElementById("lastTool");
const lastStatus = document.getElementById("lastStatus");
const lastTime = document.getElementById("lastTime");

const logsList = document.getElementById("logsList");
const refreshLogsBtn = document.getElementById("refreshLogsBtn");

let users = [];

/*
    chatHistory is sent to backend with every message.

    Format:
    [
        { role: "user", content: "Show pending approvals" },
        { role: "assistant", content: "Finance Requests: Request 2..." },
        { role: "user", content: "Approve Request 2" }
    ]
*/
let chatHistory = [];

const MAX_HISTORY_MESSAGES = 20;


function selectedUser() {
    const empId = userSelect.value;
    return users.find(user => user.emp_id === empId);
}


function updateUserCard() {
    const user = selectedUser();

    if (!user) {
        employeeId.textContent = "-";
        employeeRole.textContent = "-";
        employeeDepartment.textContent = "-";
        return;
    }

    employeeId.textContent = user.emp_id;
    employeeRole.textContent = user.role;
    employeeDepartment.textContent = user.department || "-";
}


function resetMetadata() {
    lastIntent.textContent = "-";
    lastAgent.textContent = "-";
    lastTool.textContent = "-";
    lastStatus.textContent = "-";
    lastTime.textContent = "-";
}


function saveToChatHistory(role, content) {
    if (!content || !content.trim()) {
        return;
    }

    chatHistory.push({
        role: role,
        content: content.trim()
    });

    if (chatHistory.length > MAX_HISTORY_MESSAGES) {
        chatHistory = chatHistory.slice(-MAX_HISTORY_MESSAGES);
    }
}


function addMessage(sender, text, save = true) {
    const message = document.createElement("div");
    message.className = `message ${sender}`;

    if (sender === "assistant") {
        const avatar = document.createElement("div");
        avatar.className = "avatar";
        avatar.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>`;
        message.appendChild(avatar);
    }

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;

    message.appendChild(bubble);
    chatMessages.appendChild(message);

    if (save) {
        const role = sender === "user" ? "user" : "assistant";
        saveToChatHistory(role, text);
    }

    chatMessages.scrollTop = chatMessages.scrollHeight;
}


function startNewChatForSelectedUser() {
    const user = selectedUser();

    chatMessages.innerHTML = "";
    chatHistory = [];

    if (!user) {
        addMessage(
            "assistant",
            "Hi, I am Workplace Buddy.\nPlease select a user to start chatting.",
            false
        );
        return;
    }

    addMessage(
        "assistant",
        `Hi, I am Workplace Buddy.\nYou are now chatting as ${user.name || user.emp_id} (${user.role}).\n\nI can help with HR policies, leave requests, IT tickets, asset requests, and reimbursements.`,
        false
    );

    messageInput.value = "";
    resetMetadata();
}


function setLoading(isLoading) {
    sendBtn.disabled = isLoading;
    sendBtn.textContent = isLoading ? "Thinking..." : "Send";
}


function updateMetadata(result) {
    lastIntent.textContent = result.intent || "-";
    lastAgent.textContent = result.agent || "-";
    lastTool.textContent = result.tool_used || "-";
    lastStatus.textContent = result.status || "-";
    lastTime.textContent = result.response_time ? `${result.response_time}s` : "-";
}


async function loadUsers() {
    try {
        const response = await fetch("/api/users");
        const data = await response.json();

        users = data.users || [];
        userSelect.innerHTML = "";

        users.forEach(user => {
            const option = document.createElement("option");
            option.value = user.emp_id;
            option.textContent = `${user.emp_id} - ${user.name} (${user.role})`;
            userSelect.appendChild(option);
        });

        const defaultUser = users.find(user => user.emp_id === "EMP001");

        if (defaultUser) {
            userSelect.value = defaultUser.emp_id;
        }

        updateUserCard();
        startNewChatForSelectedUser();

    } catch (error) {
        addMessage("assistant", "Unable to load users from database.", false);
    }
}


async function sendMessage(customMessage = null) {
    const user = selectedUser();

    if (!user) {
        addMessage("assistant", "Please select a user first.");
        return;
    }

    const message = customMessage || messageInput.value.trim();

    if (!message) {
        return;
    }

    addMessage("user", message);
    messageInput.value = "";

    setLoading(true);

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                emp_id: user.emp_id,
                message: message,
                chat_history: chatHistory
            })
        });

        const result = await response.json();

        if (!response.ok) {
            const errorMessage = result.detail || "Something went wrong.";
            addMessage("assistant", errorMessage);
            return;
        }

        const assistantResponse = result.response || "No response generated.";
        addMessage("assistant", assistantResponse);

        updateMetadata(result);
        loadLogs();

    } catch (error) {
        addMessage("assistant", "Server error. Please check if FastAPI is running.");
    } finally {
        setLoading(false);
    }
}


async function loadLogs() {
    try {
        const response = await fetch("/api/logs");
        const data = await response.json();

        const logs = data.logs || [];

        if (logs.length === 0) {
            logsList.innerHTML = `<p class="muted">No logs found.</p>`;
            return;
        }

        logsList.innerHTML = "";

        logs.forEach(log => {
            const item = document.createElement("div");
            item.className = "log-item";

            item.innerHTML = `
                <strong>${log.intent || "unknown"} · ${log.agent_used || "unknown"}</strong>
                <span>Emp: ${log.emp_id || "-"} | Tool: ${log.tool_used || "-"} | Status: ${log.status || "-"}</span>
                <span>${log.created_at || ""}</span>
            `;

            logsList.appendChild(item);
        });

    } catch (error) {
        logsList.innerHTML = `<p class="muted">Unable to load logs.</p>`;
    }
}


sendBtn.addEventListener("click", () => sendMessage());

messageInput.addEventListener("keydown", event => {
    if (event.key === "Enter") {
        sendMessage();
    }
});

userSelect.addEventListener("change", () => {
    updateUserCard();
    startNewChatForSelectedUser();
});

refreshLogsBtn.addEventListener("click", loadLogs);

document.querySelectorAll(".quick-btn").forEach(button => {
    button.addEventListener("click", () => {
        const message = button.getAttribute("data-message");
        sendMessage(message);
    });
});


loadUsers();
loadLogs();