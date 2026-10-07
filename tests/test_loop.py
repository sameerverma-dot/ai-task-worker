from agent.llm import ScriptedLLM
from agent.loop import run_agent
from agent.memory import RunState
from agent.tools import ToolContext
from company import app as company_app


def make_ctx(browser=None, approve=False):
    return ToolContext(browser, RunState("test goal"), ask_human=lambda q: "ok", approve=lambda s: approve)


def test_loop_stops_at_max_steps_and_reports_incomplete(tmp_path):
    llm = ScriptedLLM([("list_inbox", {"query": "globex"})])  # never calls finish
    state = run_agent(llm, make_ctx(), tmp_path, max_steps=4)
    assert len(state.steps) == 4
    assert state.final["success"] is False
    assert "INCOMPLETE" in (tmp_path / "summary.md").read_text()


def test_failures_are_retried_then_an_alternative_is_forced(tmp_path):
    llm = ScriptedLLM([("read_invoice", {"filename": "missing.pdf"})])  # keeps repeating a failing action
    state = run_agent(llm, make_ctx(), tmp_path, max_steps=5)
    observations = [s["observation"] for s in state.steps]
    # Original try + 2 retries really run (and fail)...
    assert all("not found" in o for o in observations[:3])
    # ...then the action is blocked, and the LLM was told to change approach.
    assert observations[3].startswith("BLOCKED") and observations[4].startswith("BLOCKED")
    assert "Do NOT try it again" in llm.last_user_message


def test_submit_without_approval_is_blocked(browser, tmp_path):
    llm = ScriptedLLM([
        ("browser_open", {"path": "/invoices/new"}),
        ("browser_fill", {"field_label": "Vendor", "value": "Globex"}),
        ("browser_fill", {"field_label": "Invoice No.", "value": "GLX-1"}),
        ("browser_fill", {"field_label": "Amount", "value": "10"}),
        ("browser_fill", {"field_label": "Due Date", "value": "2026-10-20"}),
        ("browser_click", {"button_text": "Submit"}),
        ("finish", {"summary": "x", "success": False, "verified": False}),
    ])
    state = run_agent(llm, make_ctx(browser), tmp_path)
    assert state.steps[5]["observation"].startswith("BLOCKED")
    assert company_app.all_invoices() == []  # nothing was written


def test_denied_approval_writes_nothing(browser, tmp_path):
    llm = ScriptedLLM([
        ("browser_open", {"path": "/invoices/new"}),
        ("request_approval", {"action_summary": "submit"}),
        ("browser_click", {"button_text": "Submit"}),
        ("finish", {"summary": "x", "success": False, "verified": False}),
    ])
    state = run_agent(llm, make_ctx(browser, approve=False), tmp_path)
    assert state.steps[1]["ok"] is False and state.steps[2]["observation"].startswith("BLOCKED")
    assert company_app.all_invoices() == []
