# Run summary

**Goal:** Find the latest invoice from Globex, extract the amount and due date, enter it into our accounts system, and tell me once it's done.

**Result:** ✅ completed

**Verification:** ✅ verified in the app

**Steps used:** 16

## Report

Found the latest Globex invoice by comparing all three Globex PDFs in the inbox: GLX-1001 (2026-07-05), GLX-1017 (2026-08-12), and GLX-1032 (2026-09-20). The latest is GLX-1032, dated 2026-09-20, with Amount INR 78,250.00 and Due Date 2026-10-20. I confirmed it was not already in the system, then entered it into Acme Accounts (Vendor = Globex, Invoice No. = GLX-1032, Amount = 78250.00, Due Date = 2026-10-20) after your approval. Verified on the saved detail page (/invoices/1): all values match the invoice exactly, status Unpaid. Done.

## Evidence

Detail page /invoices/1 shows: Vendor Globex, Invoice No. GLX-1032, Amount (INR) 78250.00, Due Date 2026-10-20, Status Unpaid — matching Globex_GLX-1032.pdf.

Step log: `steps.jsonl`. Screenshots: `screenshots/step05_browser_open.png`, `screenshots/step06_browser_read.png`, `screenshots/step07_browser_open.png`, `screenshots/step08_browser_read.png`, `screenshots/step09_browser_fill.png`, `screenshots/step10_browser_fill.png`, `screenshots/step11_browser_fill.png`, `screenshots/step12_browser_fill.png`, `screenshots/step14_browser_click.png`, `screenshots/step15_browser_read.png`
