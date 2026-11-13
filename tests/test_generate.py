import json

from doc_intake.generate_invoices import generate


def test_generates_requested_count(tmp_path):
    invoices = generate(10, tmp_path)
    assert len(invoices) == 10
    assert len(list(tmp_path.glob("*.pdf"))) == 10


def test_same_seed_gives_same_invoices(tmp_path):
    a = generate(5, tmp_path / "a", seed=7)
    b = generate(5, tmp_path / "b", seed=7)
    assert [i.true_total() for i in a] == [i.true_total() for i in b]


def test_answer_key_marks_the_defects(tmp_path):
    generate(10, tmp_path)
    key = json.loads((tmp_path / "answer_key.json").read_text())
    defects = {row["invoice_no"]: row["defect"] for row in key if row["defect"]}
    assert set(defects.values()) == {"missing_total", "bad_date", "wrong_total"}
