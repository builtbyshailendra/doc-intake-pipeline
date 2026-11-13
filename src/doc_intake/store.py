"""Save results to SQLite so they can be queried like any reporting table."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY,
    source_file TEXT NOT NULL,
    email_from TEXT,
    vendor TEXT,
    invoice_no TEXT,
    invoice_date TEXT,
    printed_total REAL,
    items_total REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('clean', 'exception'))
);
CREATE TABLE IF NOT EXISTS line_items (
    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    amount REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS exceptions (
    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
    reason TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()  # each run rebuilds the tables from the mailbox
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def save(conn: sqlite3.Connection, inv, email_from: str, issues: list[str]) -> int:
    cur = conn.execute(
        "INSERT INTO invoices (source_file, email_from, vendor, invoice_no, invoice_date, printed_total, items_total, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (inv.source_file, email_from, inv.vendor, inv.invoice_no, inv.invoice_date, inv.printed_total,
         inv.items_total(), "exception" if issues else "clean"),
    )
    invoice_id = cur.lastrowid
    conn.executemany(
        "INSERT INTO line_items VALUES (?, ?, ?, ?, ?)",
        [(invoice_id, i["description"], i["quantity"], i["unit_price"], i["amount"]) for i in inv.items],
    )
    conn.executemany("INSERT INTO exceptions VALUES (?, ?)", [(invoice_id, r) for r in issues])
    return invoice_id
