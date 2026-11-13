"""Generate synthetic invoice PDFs for testing the pipeline.

Every company, person and number here is made up. The same seed always
produces the same invoices, so tests stay repeatable.

A few invoices are deliberately broken (missing total, bad date, wrong sum)
so later steps have real exceptions to catch.

Usage:
    python -m doc_intake.generate_invoices --count 10 --out data/inbox
"""
from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

VENDORS = [
    "Northwind Supplies", "Blue Hill Logistics", "Cedar Lane Labs",
    "Riverbend Chemicals", "Summit Field Services", "Orchid Office Co",
]
CUSTOMER = "Greenleaf Environmental (synthetic)"
ITEMS = [
    ("Water sample analysis", 1800.00),
    ("Soil testing kit", 650.00),
    ("Site visit", 2500.00),
    ("Lab report", 1200.00),
    ("Courier charges", 300.00),
    ("Equipment rental (day)", 950.00),
]

# Which kind of defect to inject, if any. Index = invoice number.
DEFECTS = {3: "missing_total", 6: "bad_date", 8: "wrong_total"}


@dataclass
class LineItem:
    description: str
    quantity: int
    unit_price: float

    @property
    def amount(self) -> float:
        return round(self.quantity * self.unit_price, 2)


@dataclass
class Invoice:
    invoice_no: str
    vendor: str
    customer: str
    invoice_date: str          # kept as text on purpose: real PDFs can hold bad dates
    items: list[LineItem] = field(default_factory=list)
    printed_total: str | None = None
    defect: str | None = None

    def true_total(self) -> float:
        return round(sum(i.amount for i in self.items), 2)


def make_invoice(n: int, rng: random.Random) -> Invoice:
    base = date(2026, 10, 1)
    inv_date = base + timedelta(days=rng.randint(0, 40))
    items = [
        LineItem(desc, rng.randint(1, 4), price)
        for desc, price in rng.sample(ITEMS, k=rng.randint(2, 4))
    ]
    inv = Invoice(
        invoice_no=f"INV-{2026}{n:04d}",
        vendor=rng.choice(VENDORS),
        customer=CUSTOMER,
        invoice_date=inv_date.strftime("%d-%m-%Y"),
        items=items,
    )
    inv.printed_total = f"{inv.true_total():.2f}"

    defect = DEFECTS.get(n)
    inv.defect = defect
    if defect == "missing_total":
        inv.printed_total = None
    elif defect == "bad_date":
        inv.invoice_date = "31-02-2026"            # 31 February does not exist
    elif defect == "wrong_total":
        inv.printed_total = f"{inv.true_total() + 500:.2f}"
    return inv


def draw_pdf(inv: Invoice, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 25 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, inv.vendor)
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y - 6 * mm, "TAX INVOICE (synthetic test document)")

    y -= 20 * mm
    for label, value in [
        ("Invoice No", inv.invoice_no),
        ("Invoice Date", inv.invoice_date),
        ("Bill To", inv.customer),
    ]:
        c.drawString(20 * mm, y, f"{label}: {value}")
        y -= 6 * mm

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Description")
    c.drawString(110 * mm, y, "Qty")
    c.drawString(130 * mm, y, "Unit Price")
    c.drawString(165 * mm, y, "Amount")
    c.setFont("Helvetica", 10)
    y -= 6 * mm
    for item in inv.items:
        c.drawString(20 * mm, y, item.description)
        c.drawString(110 * mm, y, str(item.quantity))
        c.drawString(130 * mm, y, f"{item.unit_price:.2f}")
        c.drawString(165 * mm, y, f"{item.amount:.2f}")
        y -= 6 * mm

    y -= 4 * mm
    if inv.printed_total is not None:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(130 * mm, y, f"Total (INR): {inv.printed_total}")

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(20 * mm, 15 * mm, "Generated for testing. Not a real invoice.")
    c.save()


def generate(count: int, out_dir: Path, seed: int = 42) -> list[Invoice]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    invoices = []
    for n in range(1, count + 1):
        inv = make_invoice(n, rng)
        draw_pdf(inv, out_dir / f"{inv.invoice_no}.pdf")
        invoices.append(inv)

    # Answer key: what each PDF really contains. Later tests compare against it.
    key = [
        {**asdict(inv), "true_total": inv.true_total()} for inv in invoices
    ]
    (out_dir / "answer_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    return invoices


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--out", type=Path, default=Path("data/inbox"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    invoices = generate(args.count, args.out, args.seed)
    broken = [i.invoice_no for i in invoices if i.defect]
    print(f"Wrote {len(invoices)} invoices to {args.out} ({len(broken)} with deliberate defects: {', '.join(broken)})")


if __name__ == "__main__":
    main()
