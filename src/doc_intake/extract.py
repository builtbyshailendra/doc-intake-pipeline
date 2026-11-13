"""Pull structured fields out of one invoice PDF.

The extractor only reads what is printed. It never fixes anything: a missing
total stays missing and a bad date stays as text. Judging the values is the
validator's job, which keeps each step simple to test.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

LABELS = {
    "invoice_no": re.compile(r"^Invoice No:\s*(.+)$"),
    "invoice_date": re.compile(r"^Invoice Date:\s*(.+)$"),
    "customer": re.compile(r"^Bill To:\s*(.+)$"),
}
TOTAL = re.compile(r"^Total \(INR\):\s*([\d.,]+)$")
NUMBER = re.compile(r"^\d+(\.\d+)?$")


@dataclass
class Extracted:
    source_file: str
    vendor: str | None = None
    invoice_no: str | None = None
    invoice_date: str | None = None
    customer: str | None = None
    items: list[dict] = field(default_factory=list)
    printed_total: float | None = None

    def items_total(self) -> float:
        return round(sum(i["amount"] for i in self.items), 2)


def pdf_text(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def parse_text(text: str, source_file: str = "") -> Extracted:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out = Extracted(source_file=source_file, vendor=lines[0] if lines else None)

    for ln in lines:
        for key, rx in LABELS.items():
            m = rx.match(ln)
            if m:
                setattr(out, key, m.group(1).strip())
        m = TOTAL.match(ln)
        if m:
            out.printed_total = float(m.group(1).replace(",", ""))

    # Line items sit between the "Amount" column header and the total or footer,
    # four lines each: description, quantity, unit price, amount.
    if "Amount" in lines:
        start = lines.index("Amount") + 1
        block = []
        for ln in lines[start:]:
            if ln.startswith(("Total", "Generated for testing")):
                break
            block.append(ln)
        for i in range(0, len(block) - 3, 4):
            desc, qty, price, amount = block[i:i + 4]
            if not (qty.isdigit() and NUMBER.match(price) and NUMBER.match(amount)):
                continue  # skip anything that isn't a clean row
            out.items.append({"description": desc, "quantity": int(qty), "unit_price": float(price), "amount": float(amount)})
    return out


def extract(path: Path) -> Extracted:
    return parse_text(pdf_text(path), source_file=path.name)
