import sqlite3
from config import DATABASE_PATH


def get_connection():
    """
    Creates and returns a SQLite database connection.
    row_factory allows us to access columns by name.
    Example: row["emp_id"] instead of row[0]
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn