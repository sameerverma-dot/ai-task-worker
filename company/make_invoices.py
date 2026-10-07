"""Generates the sample vendor invoices (PDFs) into company/inbox/.

Run:  python -m company.make_invoices

Two layouts ("A" and "B") use different labels and date formats on purpose,
so the agent has to actually read each invoice instead of matching a template.
"""
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from config import INBOX_DIR

# (vendor, invoice no, invoice date, due date, amount INR, status, layout, line items)
INVOICES = [
    ("Globex", "GLX-1001", "2026-07-05", "2026-08-04", 45000.00, "PAID", "A",
     [("Cloud hosting - July", 45000.00)]),
    ("Globex", "GLX-1017", "2026-08-12", "2026-09-11", 62500.00, "UNPAID", "B",
     [("Cloud hosting - August", 50000.00), ("Support plan", 12500.00)]),
    ("Globex", "GLX-1032", "2026-09-20", "2026-10-20", 78250.00, "UNPAID", "A",
     [("Cloud hosting - September", 60000.00), ("Extra storage", 18250.00)]),
    ("Initech", "INI-501", "2026-08-01", "2026-08-31", 32000.00, "PAID", "B",
     [("TPS report software licence", 32000.00)]),
    ("Initech", "INI-517", "2026-09-03", "2026-10-03", 18750.00, "UNPAID", "A",
     [("Printer maintenance", 18750.00)]),
    ("Initech", "INI-522", "2026-09-15", "2026-10-15", 24300.00, "UNPAID", "B",
     [("Consulting hours (18 h)", 24300.00)]),
    ("Umbrella Corp", "UMB-2188", "2026-08-02", "2026-09-01", 15400.00, "PAID", "A",
     [("Lab safety kits", 15400.00)]),
    ("Umbrella Corp", "UMB-2201", "2026-09-10", "2026-10-10", 91000.00, "UNPAID", "B",
     [("Biohazard disposal - Q3", 91000.00)]),
    ("Acme Supplies", "ACS-77", "2026-09-05", "2026-10-05", 12600.00, "UNPAID", "A",
     [("Office stationery", 12600.00)]),
    ("Acme Supply Co", "ASC-3090", "2026-09-08", "2026-10-08", 27900.00, "UNPAID", "B",
     [("Ergonomic chairs x6", 27900.00)]),
]


def pretty_date(iso):
    """2026-10-20 -> 20 Oct 2026 (layout B uses this human style)."""
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d %b %Y")


def write_pdf(vendor, number, inv_date, due, amount, status, layout, items):
    path = INBOX_DIR / f"{vendor.replace(' ', '_')}_{number}.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    y = 800

    def line(text, size=11, gap=20):
        nonlocal y
        c.setFont("Helvetica", size)
        c.drawString(60, y, text)
        y -= gap

    if layout == "A":
        line(f"{vendor}", 18, 30)
        line("TAX INVOICE", 14, 30)
        line(f"Invoice No: {number}")
        line(f"Invoice Date: {inv_date}")
        line(f"Due Date: {due}")
        line(f"Status: {status}", gap=30)
    else:
        line(f"INVOICE from {vendor.upper()}", 16, 30)
        line(f"Invoice Number - {number}")
        line(f"Dated {pretty_date(inv_date)}")
        line(f"Payment Due By: {pretty_date(due)}")
        line(f"Payment status: {status}", gap=30)

    line("Line items:")
    for desc, price in items:
        line(f"   {desc} .......... INR {price:,.2f}")
    y -= 10
    if layout == "A":
        line(f"Total: INR {amount:,.2f}", 13)
    else:
        line(f"Amount Payable: Rs. {amount:,.2f}", 13)
    line("Bill to: Acme Corp, Accounts Payable", 9)
    c.save()
    return path


def main():
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    for inv in INVOICES:
        print("wrote", write_pdf(*inv).name)


if __name__ == "__main__":
    main()
