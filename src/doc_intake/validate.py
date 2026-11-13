"""Decide which invoices a person needs to look at, and why.

Each rule returns a short, human-readable reason. An invoice with no issues
goes straight into the clean table; anything else lands in the exceptions list.
"""
from __future__ import annotations

from datetime import datetime

from .extract import Extracted

TOLERANCE = 0.01  # rupees; rounding noise, not a real difference


def check(inv: Extracted, seen_numbers: set[str]) -> list[str]:
    issues = []

    if not inv.invoice_no:
        issues.append("Invoice number not found")
    elif inv.invoice_no in seen_numbers:
        issues.append(f"Duplicate: {inv.invoice_no} was already received")

    if not inv.invoice_date:
        issues.append("Invoice date not found")
    else:
        try:
            datetime.strptime(inv.invoice_date, "%d-%m-%Y")
        except ValueError:
            issues.append(f"Invalid date: {inv.invoice_date}")

    if not inv.items:
        issues.append("No line items found")

    if inv.printed_total is None:
        issues.append(f"Total missing (line items add up to {inv.items_total():,.2f})")
    elif abs(inv.printed_total - inv.items_total()) > TOLERANCE:
        diff = inv.printed_total - inv.items_total()
        issues.append(f"Total mismatch: printed {inv.printed_total:,.2f}, items add up to {inv.items_total():,.2f} ({diff:+,.2f})")

    return issues
