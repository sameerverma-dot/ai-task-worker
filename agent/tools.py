"""The agent's tools: plain Python functions plus a JSON description the LLM reads.

Rules every tool follows:
  * It returns {"ok": True/False, "text": "..."} and NEVER raises into the loop.
  * It is generic. Nothing here knows what an "invoice task" is; the LLM decides
    what to read, fill and click. So a new kind of task needs no code change here.
"""
from pypdf import PdfReader

from config import INBOX_DIR, NEEDS_APPROVAL


class ToolContext:
    """What the tools are allowed to touch during one run."""
    def __init__(self, browser, state, ask_human, approve):
        self.browser = browser      # agent.browser.Browser
        self.state = state          # agent.memory.RunState
        self.ask_human = ask_human  # function(question) -> answer text
        self.approve = approve      # function(summary) -> True/False


def ok(text):
    return {"ok": True, "text": text}


def fail(text):
    return {"ok": False, "text": text}


# ---------- the tools ----------

def list_inbox(ctx, query=""):
    files = sorted(p.name for p in INBOX_DIR.glob("*.pdf"))
    if query:
        files = [f for f in files if query.lower().replace(" ", "_") in f.lower()]
    return ok(f"{len(files)} file(s): {files}") if files else fail(f"No files match '{query}'.")


def read_invoice(ctx, filename):
    path = INBOX_DIR / filename.split("/")[-1]  # only files inside the inbox
    if not path.exists():
        return fail(f"File '{filename}' not found. Use list_inbox to see file names.")
    text = "\n".join(page.extract_text() for page in PdfReader(path).pages)
    ctx.state.facts[path.name] = text  # remember it, so it stays visible to the LLM
    return ok(text)


def browser_open(ctx, path):
    return ok(ctx.browser.open(path))


def browser_read(ctx):
    return ok(ctx.browser.read())


def browser_fill(ctx, field_label, value):
    return ok(ctx.browser.fill(field_label, value))


def browser_click(ctx, button_text):
    # Safety gate: buttons that change data need an approval first (and use it up).
    guarded = any(button_text.strip().lower() == b.lower() for b in NEEDS_APPROVAL)
    if guarded and not ctx.state.approved:
        return fail(f"BLOCKED: '{button_text}' changes data. Call request_approval first.")
    result = ctx.browser.click(button_text)
    if guarded:
        ctx.state.approved = False
    return ok(result)


def ask_human(ctx, question):
    return ok(f"Human answered: {ctx.ask_human(question)}")


def request_approval(ctx, action_summary):
    if ctx.approve(action_summary):
        ctx.state.approved = True
        return ok("APPROVED. You may perform this action now (approval is used up by one guarded click).")
    ctx.state.approved = False
    return fail("DENIED by the human. Do not perform this action. Finish and report it was not done.")


def finish(ctx, summary, success, verified, evidence=""):
    ctx.state.final = {"summary": summary, "success": bool(success),
                       "verified": bool(verified), "evidence": evidence}
    return ok("Run finished.")


# ---------- what the LLM sees ----------

def _schema(name, description, **params):
    """Build the JSON description of one tool. params: name -> (type, description)."""
    props = {"thought": {"type": "string", "description": "Briefly: why you are taking this step."}}
    props.update({p: {"type": t, "description": d} for p, (t, d) in params.items()})
    required = ["thought"] + [p for p in params if p != "query" and p != "evidence"]
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": props, "required": required}}}


SCHEMAS = [
    _schema("list_inbox", "List invoice PDF file names in the inbox, optionally filtered by text in the name.",
            query=("string", "Optional text to filter file names, e.g. a vendor name.")),
    _schema("read_invoice", "Read the full text of one invoice PDF from the inbox.",
            filename=("string", "Exact file name from list_inbox.")),
    _schema("browser_open", "Open a page of the Acme Accounts web app.",
            path=("string", "Path such as /invoices or /invoices/new.")),
    _schema("browser_read", "Read the current page: visible text, form fields (by label) and buttons/links."),
    _schema("browser_fill", "Type a value into a form field, found by its visible label.",
            field_label=("string", "The label exactly as shown by browser_read."),
            value=("string", "The value to type.")),
    _schema("browser_click", "Click a button or link by its visible text.",
            button_text=("string", "The button or link text as shown by browser_read.")),
    _schema("ask_human", "Ask the human a question when the task is ambiguous or you are stuck.",
            question=("string", "A clear question, listing the options if there are several.")),
    _schema("request_approval", "Ask the human to approve an action that changes data, before doing it.",
            action_summary=("string", "Exactly what you will do, including all values.")),
    _schema("finish", "End the run with a final report to the human.",
            summary=("string", "What was done, the values used, the verification result, anything uncertain."),
            success=("boolean", "True only if the task was fully completed."),
            verified=("boolean", "True only if you checked the result in the app and it matches."),
            evidence=("string", "Optional: what you saw that proves it (page, values).")),
]

FUNCTIONS = {f.__name__: f for f in [list_inbox, read_invoice, browser_open, browser_read, browser_fill,
                                     browser_click, ask_human, request_approval, finish]}


def execute(ctx, tool, args):
    """Run one tool safely. Any crash becomes a failed observation the LLM can react to."""
    if tool not in FUNCTIONS:
        return fail(f"Unknown tool '{tool}'. Available: {list(FUNCTIONS)}")
    try:
        return FUNCTIONS[tool](ctx, **args)
    except Exception as e:  # a tool must never crash the loop
        return fail(f"{type(e).__name__}: {str(e)[:400]}")
