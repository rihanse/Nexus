from database.db import get_connection


def save_memory(emp_id: str, user_message: str, assistant_response: str) -> dict:
    """
    Saves user message and assistant response into chat memory.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO chat_memory (emp_id, user_message, assistant_response)
    VALUES (?, ?, ?)
    """, (emp_id, user_message, assistant_response))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Memory saved successfully."
    }


def get_recent_memory(emp_id: str, limit: int = 5) -> list[dict]:
    """
    Gets recent conversation memory for a user.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT user_message, assistant_response, created_at
    FROM chat_memory
    WHERE emp_id = ?
    ORDER BY created_at DESC
    LIMIT ?
    """, (emp_id, limit))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]