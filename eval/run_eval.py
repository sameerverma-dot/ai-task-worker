"""Runs every task in tasks.yaml live and checks the result directly in the database.

    python -m eval.run_eval            # all tasks
    python -m eval.run_eval 1 5 6      # only some tasks
    MODEL=qwen/qwen3.8-27b python -m eval.run_eval   # pick the model

Every task runs on ONE model (no fallback), so results are comparable. If the model's daily quota
runs out, the run pauses until quota comes back, then continues.

Writes eval/results.md. Failures stay in the table with a one-line reason.
"""
import sys
import time
from pathlib import Path

import yaml

from agent.llm import GroqLLM
from company import app as company_app
from company import faults, make_invoices
from config import INBOX_DIR
from run import run_task

EVAL_DIR = Path(__file__).parent


def check(expect, state, rows):
    """Compare the end state with what we expected. Returns (passed, reason)."""
    final = state.final
    for want in expect.get("rows", []):
        matches = [r for r in rows if r["number"] == want["number"]]
        if len(matches) != 1:
            return False, f"{want['number']} found {len(matches)} times (expected once)"
        got = matches[0]
        if "amount" in want and abs(got["amount"] - want["amount"]) > 0.01:
            return False, f"{want['number']} amount {got['amount']} != {want['amount']}"
        for field in ("due_date", "status"):
            if field in want and got[field] != want[field]:
                return False, f"{want['number']} {field} '{got[field]}' != '{want[field]}'"
        if "vendor" in want and want["vendor"].lower() not in got["vendor"].lower():
            return False, f"{want['number']} vendor '{got['vendor']}' != '{want['vendor']}'"
    if "row_count" in expect and len(rows) != expect["row_count"]:
        return False, f"{len(rows)} invoices in the app, expected {expect['row_count']}"
    if expect.get("asked_human") and not any(s["tool"] == "ask_human" for s in state.steps):
        return False, "did not ask the human about the ambiguity"
    report = (final["summary"] + " " + final.get("evidence", "")).lower()
    for word in expect.get("answer_contains", []):
        if word.lower() not in report:
            return False, f"final report does not mention '{word}'"
    if "success" in expect and final["success"] != expect["success"]:
        return False, f"agent reported success={final['success']}, expected {expect['success']}"
    return True, "ok"


def run_one(task, llm):
    setup = task.get("setup", {})
    company_app.init_db(reset=True)                      # clean database for every task
    for row in setup.get("seed", []):
        company_app.add_invoice(*row)
    faults.reset(**{name: True for name in setup.get("faults", [])})
    answers = list(setup.get("human_answers", []))
    ask = lambda q: answers.pop(0) if answers else "I have no more information. Use your best judgement."
    approve = lambda summary: setup.get("approve", True)

    started = time.time()
    state, run_dir = run_task(task["task"], llm, ask, approve, video=setup.get("video", False),
                              name=f"eval{task['id']}")
    passed, reason = check(task["expect"], state, company_app.all_invoices())
    seconds = round(time.time() - started)
    return {"id": task["id"], "name": task["name"], "passed": passed, "reason": reason,
            "steps": len(state.steps), "seconds": seconds, "run": run_dir.name}


def write_results(results, model):
    passed = sum(r["passed"] for r in results)
    lines = ["# Eval results", "",
             f"Model: `{model}` for every task (live, Groq free tier). "
             f"Success rate: **{passed}/{len(results)} ({100 * passed // max(len(results), 1)}%)**", "",
             "Time is wall-clock and includes waiting for Groq's rate limits (and any pause for the daily "
             "token quota to come back), so it says more about the free tier than about the agent.", "",
             "| # | Task | Result | Steps | Time (s) | Reason | Run folder |", "|---|---|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['id']} | {r['name']} | {'✅ pass' if r['passed'] else '❌ fail'} | {r['steps']} "
                     f"| {r['seconds']} | {r['reason']} | `runs/{r['run']}` |")
    (EVAL_DIR / "results.md").write_text("\n".join(lines) + "\n")


def main():
    if not any(INBOX_DIR.glob("*.pdf")):
        make_invoices.main()
    tasks = yaml.safe_load((EVAL_DIR / "tasks.yaml").read_text())
    only = {int(a) for a in sys.argv[1:]}
    tasks = [t for t in tasks if not only or t["id"] in only]
    server = company_app.start_in_background()
    llm = GroqLLM(fallback=False)  # one model for every task
    results = []
    for task in tasks:
        print(f"\n=== Task {task['id']}: {task['name']} ===")
        results.append(run_one(task, llm))
        print(f"--> {'PASS' if results[-1]['passed'] else 'FAIL'}: {results[-1]['reason']}")
        write_results(results, llm.model)  # write after each task, so partial results survive a crash
    server.shutdown()
    faults.reset()
    print((EVAL_DIR / "results.md").read_text())


if __name__ == "__main__":
    main()
