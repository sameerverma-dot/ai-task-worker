"""THE agent loop. This is the whole "agent": a plain for-loop, no framework.

Each turn of the loop is:  Decide -> Act -> Observe -> Record.
The LLM does the deciding; tools do the acting; this file just keeps it safe and honest:
  * a hard step limit, so it can never run forever
  * failure counting, so it can't repeat the same broken action endlessly
  * a log + screenshot of every step, so a human can check what happened
"""
import json
import time

from agent.prompts import SYSTEM_PROMPT
from agent.tools import SCHEMAS, execute, fail
from config import MAX_RETRIES, MAX_STEPS


def run_agent(llm, ctx, run_dir, max_steps=MAX_STEPS):
    state = ctx.state
    (run_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    log = open(run_dir / "steps.jsonl", "w")
    warning = None  # an extra message for the LLM, e.g. "stop repeating that"

    for step in range(1, max_steps + 1):
        started = time.time()

        # 1. DECIDE: show the LLM the goal, what it knows and what happened, and get one tool call back.
        decision = llm.decide(SYSTEM_PROMPT, state.prompt_text(warning), SCHEMAS)
        tool, args = decision["tool"], decision["args"]
        thought = args.pop("thought", "")  # every tool has a "thought" field; it's for the log, not the tool
        warning = None

        # 2. ACT: run the tool, unless this exact action already failed too often.
        #    Blocking it here is what forces the LLM to try an alternative instead of looping.
        key = state.action_key(tool, args)
        if state.failures[key] > MAX_RETRIES:
            result = fail(f"BLOCKED: this exact action already failed {state.failures[key]} times. "
                          "Do something different, or ask_human.")
        else:
            result = execute(ctx, tool, args)  # never raises: errors come back as ok=False

        # 3. OBSERVE: count failures. After the original try + MAX_RETRIES retries, warn the LLM.
        if not result["ok"]:
            state.failures[key] += 1
            if state.failures[key] > MAX_RETRIES:
                warning = (f"{tool} with these arguments failed {state.failures[key]} times. "
                           "Do NOT try it again. Use a different approach or call ask_human.")

        # 4. RECORD: screenshot after every browser action, and one log line per step (evidence).
        screenshot = None
        if tool.startswith("browser_") and ctx.browser is not None:
            screenshot = f"screenshots/step{step:02d}_{tool}.png"
            try:
                ctx.browser.screenshot(run_dir / screenshot)
            except Exception:
                screenshot = None  # a missing screenshot must not stop the work
        entry = {"step": step, "thought": thought, "tool": tool, "args": args, "ok": result["ok"],
                 "observation": result["text"][:1500], "seconds": round(time.time() - started, 2),
                 "screenshot": screenshot, "model": decision.get("model", "scripted")}
        state.record(entry)
        log.write(json.dumps(entry) + "\n")
        log.flush()
        print(f"[{step:2d}] {tool}({json.dumps(args)[:100]}) -> {'OK' if result['ok'] else 'FAILED'}"
              f"  | {thought[:90]}")

        # The finish tool fills state.final; that ends the run.
        if state.final is not None:
            break
    else:
        # The for-loop ran out of steps without finish: stop safely and say so honestly.
        state.final = {"summary": f"INCOMPLETE: stopped after {max_steps} steps without finishing.",
                       "success": False, "verified": False, "evidence": "See steps.jsonl."}

    log.close()
    write_summary(state, run_dir)
    return state


def write_summary(state, run_dir):
    """summary.md: the human-readable final report."""
    f = state.final
    shots = [s["screenshot"] for s in state.steps if s["screenshot"]]
    text = (f"# Run summary\n\n**Goal:** {state.goal}\n\n"
            f"**Result:** {'✅ completed' if f['success'] else '❌ not completed'}\n\n"
            f"**Verification:** {'✅ verified in the app' if f['verified'] else '❌ not verified'}\n\n"
            f"**Steps used:** {len(state.steps)}\n\n"
            f"## Report\n\n{f['summary']}\n\n## Evidence\n\n{f.get('evidence') or '-'}\n\n"
            f"Step log: `steps.jsonl`. Screenshots: {', '.join(f'`{s}`' for s in shots) or 'none'}\n")
    (run_dir / "summary.md").write_text(text)
