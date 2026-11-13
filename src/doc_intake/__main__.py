"""Run the whole pipeline: mailbox -> PDFs -> fields -> checks -> SQLite -> report.

    python -m doc_intake demo     # make synthetic emails, then run everything
    python -m doc_intake run      # run on whatever is already in data/mailbox
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import extract, mailbox, report, store, validate
from .generate_invoices import generate


def make_demo_mailbox(data: Path) -> None:
    """Create synthetic invoices and wrap each one in an email.

    The first invoice is emailed twice, which is how duplicates usually
    happen in real inboxes: a vendor sends a reminder with the same PDF.
    """
    pdf_dir = data / "generated"
    invoices = generate(10, pdf_dir)
    box = data / "mailbox"
    box.mkdir(parents=True, exist_ok=True)
    for old in box.glob("*.eml"):
        old.unlink()
    for n, inv in enumerate(invoices, start=1):
        sender = f"billing@{inv.vendor.lower().replace(' ', '-')}.example"
        (box / f"{n:03d}.eml").write_bytes(
            mailbox.build_email(pdf_dir / f"{inv.invoice_no}.pdf", sender, f"Invoice {inv.invoice_no}"))
    first = invoices[0]
    (box / "011.eml").write_bytes(mailbox.build_email(
        pdf_dir / f"{first.invoice_no}.pdf", "billing@reminders.example", f"Reminder: invoice {first.invoice_no}"))


def run(data: Path, db_path: Path, report_path: Path) -> dict:
    attachments = mailbox.collect_attachments(data / "mailbox", data / "inbox")
    conn = store.connect(db_path)
    seen: set[str] = set()
    clean = flagged = 0
    for att in attachments:
        inv = extract.extract(att["pdf"])
        issues = validate.check(inv, seen)
        if inv.invoice_no:
            seen.add(inv.invoice_no)
        store.save(conn, inv, att["from"], issues)
        flagged += bool(issues)
        clean += not issues
    conn.commit()
    report.build(conn, report_path)
    conn.close()
    return {"emails": len(attachments), "clean": clean, "flagged": flagged, "db": db_path, "report": report_path}


def main() -> None:
    p = argparse.ArgumentParser(prog="doc_intake")
    p.add_argument("command", choices=["demo", "run"])
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--db", type=Path, default=Path("data/invoices.db"))
    p.add_argument("--report", type=Path, default=Path("reports/summary.html"))
    a = p.parse_args()
    if a.command == "demo":
        make_demo_mailbox(a.data)
    r = run(a.data, a.db, a.report)
    print(f"Processed {r['emails']} attachments: {r['clean']} ready, {r['flagged']} flagged.")
    print(f"Database: {r['db']}\nReport:   {r['report']}")


if __name__ == "__main__":
    main()
