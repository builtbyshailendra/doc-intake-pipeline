# doc-intake-pipeline

Turn PDF invoices that arrive by email into clean rows in a SQL table, flag the ones that don't add up, and produce a short report someone can check.

This is a personal learning project built on **synthetic data only**. Every company, person and amount is made up.

## Why

Many teams still have people opening emailed PDFs and typing numbers into a spreadsheet. The hard part is rarely reading the PDF. It's deciding what counts as an exception and making the result easy to trust.

## Plan

| Day | Step | Status |
|---|---|---|
| 1 | Generate 10 synthetic invoice PDFs, including 3 deliberately broken ones | Done |
| 2 | Extract fields from one PDF into JSON | |
| 3 | Process the whole batch into SQLite | |
| 4 | Validation rules and an exceptions list | |
| 5 | A one-page summary report | |
| 6 | Tests for extraction and validation in CI | |
| 7 | Read from a local mailbox folder; diagram and write-up | |

## Run it

```bash
pip install -r requirements.txt
cd src
python -m doc_intake.generate_invoices --count 10 --out ../data/inbox
cd ..
pytest -q
```

The generator writes the PDFs plus `answer_key.json`, which records what each invoice really contains. Later steps are checked against that key.

## Daily log

### Day 1: synthetic invoices

**Built:** a generator that writes 10 invoice PDFs with 2 to 4 line items each, using a fixed seed so the output is the same on every run. Three invoices carry a defect on purpose: one has no total, one is dated 31-02-2026, and one prints a total that is 500 more than its line items add up to. Three tests check the count, the repeatability and the defects. GitHub Actions runs them on every push.

**What broke:** nothing yet. The real decision was storing the invoice date as text instead of a date object. A date object can't hold 31 February, but a real PDF can, and the pipeline has to catch it rather than crash on it.

**Learned:** build the bad inputs first. Writing the answer key next to the PDFs means every later step can be tested against the truth, not against what the extractor happened to produce.
