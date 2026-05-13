from database.db import get_connection


def save_log(
    emp_id: str,
    user_query: str,
    intent: str,
    agent_used: str,
    tool_used: str,
    status: str,
    response_time: float = 0.0
) -> dict:
    """
    Saves execution log for observability.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO logs (
        emp_id,
        user_query,
        intent,
        agent_used,
        tool_used,
        status,
        response_time
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        emp_id,
        user_query,
        intent,
        agent_used,
        tool_used,
        status,
        response_time
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Log saved successfully."
    }


def get_recent_logs(limit: int = 20) -> list[dict]:
    """
    Gets recent system logs.
    """

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM logs
    ORDER BY created_at DESC
    LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]