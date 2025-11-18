import sqlite3
import os
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "crisis.db")

def init_db():
    """Initialize the SQLite database with events table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            type TEXT,
            title TEXT,
            description TEXT,
            severity REAL,
            lat REAL,
            lon REAL,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def upsert_events(events: List[Dict[str, Any]]):
    """Insert or update events in the database."""
    if not events:
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for event in events:
        c.execute("""
            INSERT OR REPLACE INTO events
            (id, source, type, title, description, severity, lat, lon, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get("id"),
            event.get("source"),
            event.get("type"),
            event.get("title"),
            event.get("description"),
            event.get("severity"),
            event.get("lat"),
            event.get("lon"),
            event.get("updated_at")
        ))

    conn.commit()
    conn.close()

def read_events() -> List[Dict[str, Any]]:
    """Read all events from the database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM events")
    rows = c.fetchall()

    events = []
    for row in rows:
        events.append({
            "id": row["id"],
            "source": row["source"],
            "type": row["type"],
            "title": row["title"],
            "description": row["description"],
            "severity": row["severity"],
            "lat": row["lat"],
            "lon": row["lon"],
            "updated_at": row["updated_at"]
        })

    conn.close()
    return events
