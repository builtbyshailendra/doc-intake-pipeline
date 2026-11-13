import json
import sqlite3

from doc_intake import extract, validate
from doc_intake.__main__ import make_demo_mailbox, run
from doc_intake.generate_invoices import generate


def test_extractor_matches_answer_key(tmp_path):
    generate(10, tmp_path)
    key = {row["invoice_no"]: row for row in json.loads((tmp_path / "answer_key.json").read_text())}
    for pdf in tmp_path.glob("*.pdf"):
        got = extract.extract(pdf)
        want = key[got.invoice_no]
        assert got.vendor == want["vendor"]
        assert got.invoice_date == want["invoice_date"]
        assert got.items_total() == want["true_total"]
        assert len(got.items) == len(want["items"])
        expected_total = None if want["printed_total"] is None else float(want["printed_total"])
        assert got.printed_total == expected_total


def test_validator_flags_each_defect_type():
    good = extract.parse_text("V\nInvoice No: A-1\nInvoice Date: 01-11-2026\nAmount\nX\n2\n10.00\n20.00\nTotal (INR): 20.00")
    assert validate.check(good, set()) == []

    no_total = extract.parse_text("V\nInvoice No: A-2\nInvoice Date: 01-11-2026\nAmount\nX\n1\n5.00\n5.00")
    assert any("Total missing" in r for r in validate.check(no_total, set()))

    bad_date = extract.parse_text("V\nInvoice No: A-3\nInvoice Date: 31-02-2026\nAmount\nX\n1\n5.00\n5.00\nTotal (INR): 5.00")
    assert any("Invalid date" in r for r in validate.check(bad_date, set()))

    wrong = extract.parse_text("V\nInvoice No: A-4\nInvoice Date: 01-11-2026\nAmount\nX\n1\n5.00\n5.00\nTotal (INR): 505.00")
    assert any("Total mismatch" in r for r in validate.check(wrong, set()))

    assert any("Duplicate" in r for r in validate.check(good, {"A-1"}))


def test_end_to_end_demo(tmp_path):
    make_demo_mailbox(tmp_path)
    result = run(tmp_path, tmp_path / "out.db", tmp_path / "report.html")
    assert result == {**result, "emails": 11, "clean": 7, "flagged": 4}

    conn = sqlite3.connect(tmp_path / "out.db")
    reasons = [r for (r,) in conn.execute("SELECT reason FROM exceptions")]
    assert any(r.startswith("Duplicate") for r in reasons)
    assert any(r.startswith("Invalid date") for r in reasons)
    assert any(r.startswith("Total missing") for r in reasons)
    assert any(r.startswith("Total mismatch") for r in reasons)
    assert "Needs attention" in (tmp_path / "report.html").read_text(encoding="utf-8")
