"""
db.py — database connection management.

Provides a single function to get a SQLite connection with
foreign key enforcement enabled. All other modules call
get_connection() rather than managing connections themselves.
"""

import sqlite3
from pathlib import Path


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open and return a SQLite connection with FK enforcement on."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialise_database(db_path: str, schema_path: str) -> None:
    """Create all tables from the schema DDL if they don't exist."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    ddl = Path(schema_path).read_text()
    conn = get_connection(db_path)
    conn.executescript(ddl)
    conn.close()
