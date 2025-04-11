import sqlite3
from datetime import datetime

def init_db():
    with sqlite3.connect("experiments.db") as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY,
            lr REAL,
            epochs INTEGER,
            batch_size INTEGER,
            accuracy REAL,
            runtime REAL,
            status TEXT,
            current_epoch INTEGER DEFAULT 0,
            loss REAL DEFAULT 0
        )
        """)
        conn.commit()

def insert_experiment(lr, epochs, batch_size):
    with sqlite3.connect("experiments.db") as conn:
        c = conn.cursor()
        c.execute("INSERT INTO experiments (lr, epochs, batch_size, status) VALUES (?, ?, ?, 'running')",
                  (lr, epochs, batch_size))
        conn.commit()
        return c.lastrowid

def update_experiment(id, **kwargs):
    with sqlite3.connect("experiments.db") as conn:
        keys = ", ".join([f"{k}=?" for k in kwargs])
        values = list(kwargs.values())
        values.append(id)
        conn.execute(f"UPDATE experiments SET {keys} WHERE id=?", values)
        conn.commit()

def get_all_experiments(sort_key="accuracy", direction="desc"):
    if sort_key not in ["accuracy", "runtime"]:  # basic safety check
        sort_key = "accuracy"
    direction = direction.upper()
    with sqlite3.connect("experiments.db") as conn:
        c = conn.cursor()
        c.execute(f"SELECT * FROM experiments ORDER BY {sort_key} {direction}")
        rows = c.fetchall()
        return [dict(zip([c[0] for c in c.description], row)) for row in rows]

def get_running_jobs():
    with sqlite3.connect("experiments.db") as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM experiments WHERE status='running'")
        rows = c.fetchall()
        return [dict(zip([c[0] for c in c.description], row)) for row in rows]

def job_exists(lr, epochs, batch_size):
    with sqlite3.connect("experiments.db") as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM experiments WHERE lr=? AND epochs=? AND batch_size=?", (lr, epochs, batch_size))
        return c.fetchone() is not None
