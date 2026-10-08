# Run summary

**Goal:** Looking at the invoices in the inbox, which vendor has the highest total amount still due (unpaid invoices)? Do not change anything.

**Result:** ✅ completed

**Verification:** ✅ verified in the app

**Steps used:** 13

## Report

Unpaid (UNPAID) invoice totals per vendor:
- Umbrella Corp: UMB-2201 = INR 91,000.00 (UMB-2188 is PAID) → total due INR 91,000.00
- Globex: GLX-1017 = INR 62,500.00 + GLX-1032 = INR 78,250.00 (GLX-1001 is PAID) → total due INR 140,750.00
- Initech: INI-517 = INR 18,750.00 + INI-522 = INR 24,300.00 (INI-501 is PAID) → total due INR 43,050.00
- Acme Supply Co: ASC-3090 = INR 27,900.00 → total due INR 27,900.00
- Acme Supplies: ACS-77 = INR 12,600.00 → total due INR 12,600.00

Answer: Globex has the highest total amount still due, INR 140,750.00 (two unpaid invoices: GLX-1017 for 62,500.00 and GLX-1032 for 78,250.00). Note: "Acme Supplies" and "Acme Supply Co" were treated as two separate vendors based on their distinct names/invoice numbers; if they are actually the same vendor, their combined unpaid total would be INR 40,500.00, which still does not exceed Globex. No changes were made to the app.

## Evidence

Read all 10 inbox invoices. Unpaid amounts: Globex GLX-1017 Rs. 62,500.00 + GLX-1032 INR 78,250.00 = 140,750.00; Umbrella Corp UMB-2201 Rs. 91,000.00; Initech INI-517 18,750.00 + INI-522 24,300.00 = 43,050.00; Acme Supply Co ASC-3090 27,900.00; Acme Supplies ACS-77 12,600.00. PAID invoices (Globex GLX-1001, Initech INI-501, Umbrella UMB-2188) excluded.

Step log: `steps.jsonl`. Screenshots: none
