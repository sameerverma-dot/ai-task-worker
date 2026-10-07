# AI Task Worker

An AI worker that takes a plain-English task and completes it by itself inside a small **simulated company**: a folder of vendor invoice PDFs and an internal web app, "Acme Accounts", that it drives through a real browser.

> "Find the latest invoice from Globex, extract the amount and due date, enter it into our accounts system, and tell me once it's done."

It plans, uses tools, recovers from injected failures, asks a human when something is ambiguous or about to change data, **verifies the result in the app's UI**, and leaves evidence: a step log, screenshots, a summary and an optional video.

## How to run

```bash
pip install -r requirements.txt          # Chromium must be available to Playwright
export GROQ_API_KEY=...                   # read from the environment only, never stored
python -m company.make_invoices           # creates the 10 sample PDFs (run.py also does this if needed)

python run.py "Find the latest invoice from Globex, extract the amount and due date, enter it into our accounts system, and tell me once it's done."
python run.py "<task>" --auto-approve --video --fault FAIL_FIRST_SUBMIT   # demo with an injected failure

python -m pytest                          # offline tests, no API key needed (scripted LLM)
python -m eval.run_eval                   # live eval of all 10 tasks -> eval/results.md
python -m company.app                     # just the web app, at http://127.0.0.1:5055/invoices
python try_tools.py                       # calls the tools directly, no LLM (fills and submits by labels)
```

Each run writes `runs/<timestamp>/`: `steps.jsonl` (thought, tool, arguments, observation and time for every step), `screenshots/`, `summary.md` (with a ✅/❌ verification line), and `video.webm` with `--video`.

## Architecture

```
  task (plain English)
        │
        ▼
 ┌──────────────────────────── agent/loop.py ─────────────────────────────┐
 │  for step in range(MAX_STEPS):                                          │
 │     1. DECIDE   llm.decide(system prompt + goal + facts + history)      │──► agent/llm.py
 │     2. ACT      tools.execute(tool, args)      (never raises)           │     GroqLLM / ScriptedLLM
 │     3. OBSERVE  ok / FAILED; count failures; block after 2 retries      │
 │     4. RECORD   steps.jsonl + screenshot                                │──► runs/<timestamp>/
 │     stop on finish; out of steps → "INCOMPLETE"                         │
 └─────────────┬──────────────────────────────────────────────────────────┘
               │ agent/tools.py: generic tools only
   ┌───────────┼──────────────────────┬──────────────────────────┐
   ▼           ▼                      ▼                          ▼
 list_inbox  browser_open/read/      ask_human               finish
 read_invoice fill/click             request_approval         (summary, success, verified)
   │           │ agent/browser.py (Playwright, by label/text)
   ▼           ▼
 company/inbox/*.pdf   company/app.py "Acme Accounts" (Flask + SQLite)  ◄── company/faults.py
```

| File | What it does |
|---|---|
| `agent/loop.py` | The agent loop: a plain, commented `for` loop |
| `agent/tools.py` | The 9 tools plus the JSON descriptions the LLM sees; the approval gate |
| `agent/browser.py` | Playwright wrapper: open, read, fill by label, click by text, screenshot |
| `agent/llm.py` | `GroqLLM` (real model, tool calling) and `ScriptedLLM` (offline fake), same interface |
| `agent/memory.py` | Run state: documents read, steps, failure counts; builds the condensed prompt |
| `agent/prompts.py` | The rules of behaviour, in plain English |
| `company/` | The simulated company: the PDF generator, the web app and the fault switches |
| `eval/` | 10 tasks with expected database end states, and the runner |

## Design decisions

- **A plain loop, no framework.** The whole agent is about 90 lines anyone can read. Safety rules are visible `if` statements.
- **Generic tools.** No tool knows what an invoice is: they read pages, fill by *label*, click by *visible text*. The task logic lives in the LLM, so new tasks need no code. It's also why the `RENAME_FIELD` fault doesn't break anything: the agent reads the page and uses the new label.
- **Safety enforced in code, not only in the prompt.** `browser_click` refuses any button in `config.NEEDS_APPROVAL` unless `request_approval` was approved just before, and one approval allows one click. A failing action is blocked after 2 retries, and the step limit can't be bypassed.
- **Verification through the UI, checked independently.** The agent must re-read the list or detail page and compare values before claiming `verified=true`. The eval then checks the SQLite database directly, with a checker the agent never sees.
- **Honest failure.** HTTP error pages count as failures; running out of steps reports "INCOMPLETE"; impossible tasks must finish with `success=false`.
- **Small prompts.** The free Groq tier allows 8k tokens/minute, so each step re-sends only the goal, the documents read, and a condensed history: older steps are reduced to one line, older page reads are shortened, and invoice text isn't repeated.

## Results

All numbers are from live runs against Groq's **free tier**. Failures are kept, with a one-line reason.

### The free-tier quota limit (read this first)

Groq's free tier limits each model to **8,000 tokens per minute** and **200,000 tokens per day** (a rolling 24-hour window). One task uses roughly **40–50k tokens**, because the whole prompt is re-sent at every step. So:

- **one model can run only about 4 tasks per day**, and a full 10-task eval (≈450k tokens) can't run on a single model in one session;
- every step waits ~15–30 s for the per-minute limit, so a task takes 3–12 minutes;
- the paid Dev tier, which would remove this, wasn't available while this was built.

To get through all 10 tasks anyway, the eval was run in parts, using whichever model still had quota. When a model's daily quota ran out mid-task, `GroqLLM` switched to the next model (`gpt-oss-120b` → `qwen3.8-27b` → `gpt-oss-20b`). Each task's row lists the model(s) that actually made its decisions, and every step in `steps.jsonl` records its model. **Results from different models are not directly comparable.** `gpt-oss-20b`, the last fallback, is clearly the weakest of the three.

`python -m eval.run_eval` (no `--fallback`) runs every task on one model and pauses when its quota runs out. With a full day's quota, or the Dev tier, that gives a clean single-model result.

### Results by task

RESULTS_TABLE

### Earlier runs on `openai/gpt-oss-120b`

Before its daily quota ran out, gpt-oss-120b passed every task it was given:

| Task | Result | Steps | Time (s) | Run folder |
|---|---|---|---|---|
| 1. Main Globex task (Milestone 3) | ✅ pass, verified in UI | 18 | 218 | `runs/20261007-172655` |
| 4. Ambiguous Acme → asked the human | ✅ pass | 18 | 202 | `runs/20261007-173051-eval4` |
| 5. Main task + `FAIL_FIRST_SUBMIT` → recovered from the 500 | ✅ pass | 27 | 367 | `runs/20261007-173412-eval5` |
| 6. Main task + `RENAME_FIELD` + `SLOW_PAGE` → used the new label | ✅ pass | 22 | 158 | `runs/20261007-174019-eval6` |
| 7. Already entered → no duplicate created | ✅ pass | 12 | 77 | `runs/20261007-174258-eval7` |

### Demo video

**`runs/demo-replay-task5/video.webm`** (56 s): the main task with the `FAIL_FIRST_SUBMIT` fault. The agent reads the invoices, fills the form by its labels, asks for approval and submits. The app returns a **500**; the agent reads the error, goes back, refills the form, asks for approval again, resubmits, and verifies the saved invoice on its detail page.

**This is a replay, not a live LLM run.** By the time the video was recorded, every model's free-tier quota was used up. So the *decisions* come from the logged, successful live gpt-oss-120b run (`runs/20261007-173412-eval5/steps.jsonl`). They're fed back through the real loop with the scripted LLM, and the browser, app, injected 500, approval gate and verification all run for real. It's reproducible with:

```bash
python -m eval.replay_run runs/20261007-173412-eval5 --fault FAIL_FIRST_SUBMIT
```

`run.py --video` records a live run the same way when quota is available.

### A bug the eval found

In run 1, task 5's Submit failed three times for three *different* reasons: the injected 500, a missing approval, then a missing field. The loop counted that as "the same action failed 3 times" and blocked Submit for the rest of the run, even after the agent had fixed the form. **Fix:** failures are now counted *in a row*, so any successful step resets the count (`agent/loop.py`). There's a regression test in `tests/test_loop.py`.

### Offline tests

`python -m pytest`: **8 passed**, no API key needed. The tests cover:
- filling by label, including after `RENAME_FIELD`;
- stopping at `MAX_STEPS` with "INCOMPLETE";
- retry then forced alternative, and the reset after a success;
- Submit blocked without approval;
- denied approval writes nothing;
- duplicate invoice numbers rejected by the app.

## Assumptions

- Amounts are in INR. The app stores dates as `YYYY-MM-DD`; the agent converts layouts like "20 Oct 2026".
- "Unpaid" means the invoice PDF says `UNPAID`. "Latest" means the latest invoice date.
- Task 8 ("highest amount due") is answered from the inbox PDFs, not the app.
- The human is the person at the CLI. In the eval, their answers and approvals are scripted.

## Known limitations

- **Free-tier quota:** 200k tokens per model per day, so about 4 tasks per model per day; see Results. The full eval couldn't run on a single model in one session.
- **Speed:** about 15–30 s per step, mostly waiting for the per-minute rate limit; a task takes 3–12 minutes.
- **Prompt size:** the whole condensed history is re-sent at every step, and that's what drives token use. Prompt caching or a multi-field fill tool would cut it a lot.
- One field per `browser_fill` call costs steps; `MAX_STEPS` was raised from 25 to 40 so two-invoice tasks fit.
- The model sometimes takes redundant steps (re-listing the inbox, asking for approval before the last field is filled). The code-level gates make that safe, not efficient.
- Results vary between runs because the LLM is not deterministic; the eval is a single run per task.
- `read_invoice` uses text extraction (pypdf), so scanned image PDFs would need OCR.

## What next

- A `browser_fill_form` tool that fills several fields at once (fewer steps and tokens).
- Run each eval task several times and report pass rates, not single runs.
- A paid or local model for speed; prompt caching.
- More tools (dropdowns, file upload), and approvals sent to Slack or email instead of the CLI.

## Models and tools used

- **LLM at runtime:** `openai/gpt-oss-120b` on Groq, with tool calling (set in `config.py`). When a model's daily quota runs out, it falls back to `qwen/qwen3.8-27b` and then `openai/gpt-oss-20b`. The spec's default, `llama-3.3-70b-versatile`, is no longer offered by Groq.
- **Libraries:** Flask, Playwright (Chromium), pypdf, reportlab, groq, pydantic, PyYAML, pytest.
- **Built with Claude Code** (Anthropic's coding agent), following `TASK_WORKER_SPEC.md` milestone by milestone, running each milestone before committing.

See `DESIGN_DECISIONS.md` for the reasoning behind the main design choices.
