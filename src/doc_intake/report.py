"""Write a one-page HTML summary a finance person can read in a minute."""
from __future__ import annotations

import html
import sqlite3
from datetime import datetime
from pathlib import Path

CSS = """
:root{--bg:#f6f7fb;--card:#fff;--ink:#1d2433;--muted:#667085;--line:#e6e8ef;--ok:#127a5b;--okbg:#e6f5ef;--bad:#b42318;--badbg:#fdecea;--accent:#3b4cca}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Segoe UI",system-ui,-apple-system,Arial,sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 20px 48px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:24px}
h1{margin:0;font-size:26px}h2{font-size:17px;margin:32px 0 12px}.sub{color:var(--muted);margin:4px 0 0}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.card .k{color:var(--muted);font-size:13px}.card .v{font-size:28px;font-weight:650;margin-top:2px}
.card.bad .v{color:var(--bad)}.card.ok .v{color:var(--ok)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f0f2f8;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
tr:last-child td{border-bottom:0}.num{text-align:right;font-variant-numeric:tabular-nums}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600}
.pill.clean{background:var(--okbg);color:var(--ok)}.pill.exception{background:var(--badbg);color:var(--bad)}
ul.reasons{margin:0;padding-left:18px;color:var(--bad)}
footer{color:var(--muted);font-size:12px;margin-top:28px}
"""


def money(x) -> str:
    return "-" if x is None else f"{x:,.2f}"


def build(conn: sqlite3.Connection, out_path: Path) -> Path:
    rows = conn.execute(
        "SELECT id, invoice_no, vendor, invoice_date, printed_total, items_total, status, email_from FROM invoices ORDER BY invoice_no, id"
    ).fetchall()
    reasons = {}
    for invoice_id, reason in conn.execute("SELECT invoice_id, reason FROM exceptions"):
        reasons.setdefault(invoice_id, []).append(reason)

    clean = [r for r in rows if r[6] == "clean"]
    flagged = [r for r in rows if r[6] == "exception"]
    clean_value = sum(r[5] for r in clean)
    by_vendor = conn.execute(
        "SELECT vendor, COUNT(*), SUM(items_total) FROM invoices WHERE status='clean' GROUP BY vendor ORDER BY SUM(items_total) DESC"
    ).fetchall()

    e = html.escape
    parts = [f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Invoice intake summary</title><style>{CSS}</style></head><body><main>
<header><div><h1>Invoice intake summary</h1><p class="sub">Synthetic data. Generated {datetime.now():%d %b %Y, %H:%M}</p></div></header>
<section class="cards">
<div class="card"><div class="k">Invoices received</div><div class="v">{len(rows)}</div></div>
<div class="card ok"><div class="k">Ready to post</div><div class="v">{len(clean)}</div></div>
<div class="card bad"><div class="k">Need a person to check</div><div class="v">{len(flagged)}</div></div>
<div class="card"><div class="k">Value ready to post (INR)</div><div class="v">{clean_value:,.0f}</div></div>
</section>"""]

    parts.append("<h2>Needs attention</h2>")
    if flagged:
        parts.append("<table><tr><th>Invoice</th><th>Vendor</th><th>Why it was flagged</th></tr>")
        for r in flagged:
            items = "".join(f"<li>{e(x)}</li>" for x in reasons.get(r[0], []))
            parts.append(f"<tr><td>{e(r[1] or '-')}</td><td>{e(r[2] or '-')}</td><td><ul class='reasons'>{items}</ul></td></tr>")
        parts.append("</table>")
    else:
        parts.append("<p>Nothing to check.</p>")

    parts.append("<h2>All invoices</h2><table><tr><th>Invoice</th><th>Vendor</th><th>Date</th><th class='num'>Printed total</th><th class='num'>Items total</th><th>Status</th></tr>")
    for r in rows:
        label = "Ready" if r[6] == "clean" else "Check"
        parts.append(f"<tr><td>{e(r[1] or '-')}</td><td>{e(r[2] or '-')}</td><td>{e(r[3] or '-')}</td>"
                     f"<td class='num'>{money(r[4])}</td><td class='num'>{money(r[5])}</td><td><span class='pill {r[6]}'>{label}</span></td></tr>")
    parts.append("</table>")

    parts.append("<h2>Ready to post, by vendor</h2><table><tr><th>Vendor</th><th class='num'>Invoices</th><th class='num'>Value (INR)</th></tr>")
    for v, n, total in by_vendor:
        parts.append(f"<tr><td>{e(v)}</td><td class='num'>{n}</td><td class='num'>{money(total)}</td></tr>")
    parts.append("</table><footer>doc-intake-pipeline · personal learning project · all data is synthetic</footer></main></body></html>")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return out_path
