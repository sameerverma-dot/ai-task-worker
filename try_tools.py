"""Milestone 2 check: call the tools directly, no LLM. Fills and submits the form by labels.

Run:  python try_tools.py
"""
from agent.browser import Browser
from agent.memory import RunState
from agent.tools import ToolContext, execute
from company import app as company_app
from config import APP_URL

company_app.init_db(reset=True)
server = company_app.start_in_background()
browser = Browser(APP_URL)
ctx = ToolContext(browser, RunState("manual test"), ask_human=input, approve=lambda s: True)

for tool, args in [
    ("list_inbox", {"query": "globex"}),
    ("read_invoice", {"filename": "Globex_GLX-1032.pdf"}),
    ("browser_open", {"path": "/invoices/new"}),
    ("browser_read", {}),
    ("browser_fill", {"field_label": "Vendor", "value": "Globex"}),
    ("browser_fill", {"field_label": "Invoice No.", "value": "GLX-1032"}),
    ("browser_fill", {"field_label": "Amount", "value": "78250.00"}),
    ("browser_fill", {"field_label": "Due Date", "value": "2026-10-20"}),
    ("browser_click", {"button_text": "Submit"}),             # blocked: no approval yet
    ("request_approval", {"action_summary": "Submit GLX-1032"}),
    ("browser_click", {"button_text": "Submit"}),
    ("browser_open", {"path": "/invoices"}),
    ("browser_read", {}),
]:
    result = execute(ctx, tool, args)
    print(f"\n>>> {tool}({args})\n{'OK' if result['ok'] else 'FAILED'}: {result['text']}")

browser.close()
server.shutdown()
