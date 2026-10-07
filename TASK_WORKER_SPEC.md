# Build spec: Autonomous AI Task Worker (CentrAlign AI intern task)

Hand this file to Claude Code. Put it at the root of a **new, empty repo** `ai-task-worker`, then paste the kickoff prompt at the bottom.

**Hard stop: 3:30 AM.** Submit with whatever runs end to end at that point. Nothing half-built goes in the README as "working".

**The owner (Sam) is not a strong coder and must explain and modify this system live in an interview.** This shapes every decision below: small, plain Python, no agent frameworks, no clever abstractions. Readability beats elegance.

---

## 1. What we're building

An AI worker that takes a plain-English task and completes it on a computer by itself, inside a **simulated company**:

- a folder of vendor invoices (PDFs)
- a small internal web app ("Acme Accounts") where invoices are entered and listed

Main demo task (their own example):
> "Find the latest invoice from Globex, extract the amount and due date, enter it into our accounts system, and tell me once it's done."

The agent runs the loop **Goal → Plan → Act → Observe → Adapt → Verify → Report**, using tools, and it:
- asks a human when the task is ambiguous or before an irreversible action
- recovers from injected failures
- verifies the result through the app's UI, not by trusting itself
- returns evidence: a step log, screenshots and a short summary

## 2. Hard constraints

- **Python 3.10+.** Dependencies are limited to: `flask`, `playwright`, `pypdf`, `reportlab` (only to generate the sample invoices), `groq`, `pydantic`, `pytest`. Pin versions in `requirements.txt`.
- **No LangChain, LangGraph, CrewAI or any agent framework.** The agent loop is a plain `for` loop that we write ourselves. This is deliberate: it's the part Sam must explain.
- **LLM:** the Groq API with tool calling. Model in `config.py` (default `llama-3.3-70b-versatile`; switch if tool calling misbehaves). Read the key only from env `GROQ_API_KEY`. Never print it, never commit `.env`. Add `.env` to `.gitignore` before the first commit.
- **A `ScriptedLLM` mock provider,** so all tests run offline with no key.
- **Use only the mock company.** No real websites and no real credentials.
- Use the Chromium that's already installed; do not run `playwright install` if the browser is already available.
- Total code (excluding tests and data) should stay under ~800 lines. If it grows past that, simplify.

## 3. Repo layout

```
ai-task-worker/
  README.md
  requirements.txt
  config.py              # model name, max_steps, paths, app URL
  run.py                 # CLI: python run.py "task text" [--auto-approve] [--video]
  agent/
    loop.py              # THE agent loop (~100 lines, heavily commented)
    tools.py             # tool functions + their JSON schemas for the LLM
    browser.py           # thin Playwright wrapper: open, read_page, fill, click, screenshot
    llm.py               # GroqLLM + ScriptedLLM, same interface
    memory.py            # run state: facts found, steps taken, retries
    prompts.py           # system prompt (rules of behaviour)
  company/
    app.py               # Flask "Acme Accounts" app + SQLite
    templates/           # list page, new-invoice form, invoice detail
    faults.py            # failure injection switches
    make_invoices.py     # generates sample PDFs into company/inbox/
    inbox/               # generated invoice PDFs
  eval/
    tasks.yaml           # 8–10 tasks with expected end state
    run_eval.py          # runs all tasks, checks DB state, writes results table
  runs/<timestamp>/      # per run: steps.jsonl, screenshots/, summary.md, video.webm
  tests/
```

## 4. The simulated company

### 4.1 Invoice inbox (`make_invoices.py`)
- About 10 PDFs from 4 vendors: Globex, Initech, Umbrella Corp, and **two similar ones, "Acme Supplies" and "Acme Supply Co"** (for the ambiguity test).
- Each PDF has: vendor, invoice number, invoice date, due date, amount (INR), and line items.
- Globex has 3 invoices on different dates, so "latest" requires real comparison.
- Vary the layouts slightly (label "Due Date" vs "Payment Due By", amount as "Total" vs "Amount Payable"), so extraction isn't a fixed template.

### 4.2 "Acme Accounts" web app (`app.py`)
- `/invoices`: a table of entered invoices (vendor, number, amount, due date, status).
- `/invoices/new`: a form with labelled fields, Vendor, Invoice No., Amount, Due Date, and a Submit button.
- `/invoices/<id>`: a detail page with a "Mark as paid" button.
- Data lives in SQLite. **Duplicate invoice numbers are rejected** with a visible error message.

### 4.3 Fault injection (`faults.py`, set by env vars or CLI flags)
- `FAIL_FIRST_SUBMIT`: the first form submit returns a 500 error page. The agent must notice and retry.
- `RENAME_FIELD`: the "Due Date" label becomes "Payment Due". The agent must find the field by reading the page, not by a hard-coded selector.
- `SLOW_PAGE`: random 1–3 s delay on load. The browser wrapper must wait properly.

## 5. The agent

### 5.1 Tools (`tools.py`)
Each tool is a plain Python function plus a JSON schema the LLM sees. Every tool returns a short text observation, and an `ok: false` plus reason on failure; tools never raise into the loop.

| Tool | Does |
|---|---|
| `list_inbox(query?)` | Lists invoice files, optionally filtered by text |
| `read_invoice(filename)` | Extracts the text of one PDF (pypdf) |
| `browser_open(path)` | Opens an app page |
| `browser_read()` | Returns the visible text, the form fields (by label) and the buttons of the current page |
| `browser_fill(field_label, value)` | Fills a field by its visible label |
| `browser_click(button_text)` | Clicks a button or link by its visible text |
| `ask_human(question)` | Asks the user (CLI input; scripted answers in eval) |
| `request_approval(action_summary)` | Must be called before the final submit; returns approved or denied |
| `finish(summary, evidence)` | Ends the run with the final report |

**Generalization rule:** tools are generic (read page, fill by label, click by text). **No tool may know what an invoice task is.** The task-specific thinking happens in the LLM. This is what lets a new task run without code changes.

### 5.2 The loop (`loop.py`)

```
state = new run state (goal, facts, steps, retries)
for step in range(max_steps):            # max_steps = 25
    action = llm.decide(system_prompt, goal, state, tool_schemas)
    observation = execute(action)          # a tool call, never raises
    state.record(action, observation, screenshot_if_browser)
    if action is finish: break
    if observation failed: state.retries[action] += 1
         if retries > 2 for same action: tell the LLM to try an alternative or ask_human
else:
    stop safely, report "incomplete", with evidence
```

Comment this file generously. Every block gets a plain-English comment saying *why*, not just what.

### 5.3 System prompt rules (`prompts.py`)
- Plan briefly first: state the steps you think are needed.
- Never invent values. Every value you enter must come from a document you read in this run.
- Before any submit or irreversible click, call `request_approval`.
- If two candidates match (e.g. two "Acme" vendors), call `ask_human`. Don't guess.
- After acting, **verify**: open the list or detail page, read it, and confirm that the values match what you extracted.
- `finish` must include what was done, the values, the verification result, and anything uncertain.

### 5.4 Memory (`memory.py`)
- A simple dict of facts discovered (e.g. `{"globex_latest": {...}}`) plus a step list.
- A condensed history goes to the LLM each step: the last ~8 steps in full, and older ones summarised in one line each, to keep the context small.

### 5.5 Evidence (`runs/<timestamp>/`)
- `steps.jsonl`: one line per step, with the thought or plan, the tool, its arguments, the observation and the time taken.
- `screenshots/`: one per browser action.
- `summary.md`: the final report, with a ✅/❌ verification line.
- `video.webm`: only with `--video` (Playwright `record_video_dir`). This becomes the demo video.

## 6. Eval (`eval/`)
8–10 tasks, each with an **expected end state checked directly in SQLite** (the agent never sees this checker):

1. Latest Globex invoice → entered correctly (the main demo).
2. All unpaid Initech invoices → all entered, no duplicates.
3. Mark Umbrella invoice #X as paid → status changed.
4. "Enter the Acme invoice" (ambiguous) → agent must `ask_human`; a scripted answer picks one, then it's entered.
5. The main task with `FAIL_FIRST_SUBMIT` → still entered exactly once.
6. The main task with `RENAME_FIELD` → still entered correctly.
7. An invoice that is already entered → agent detects the duplicate and does **not** create a second record.
8. "Which vendor has the highest total amount due?" (read-only) → correct answer, and the DB is unchanged.
9. A task the system can't do ("email the vendor") → the agent reports it can't do it; no fake success.
10. (optional) Approval denied → nothing is written.

`run_eval.py` writes `eval/results.md` with:
- pass/fail per task
- steps used
- time taken
- overall success rate

**Report the real numbers.** Failures stay in the table with a one-line reason.

## 7. Tests (pytest, offline, ScriptedLLM)
- The browser wrapper fills a field by label, and still finds it after `RENAME_FIELD`.
- The loop stops at `max_steps` and reports "incomplete".
- A failed tool observation leads to a retry, and after 2 retries an alternative is forced.
- Submit without approval is blocked.
- The duplicate invoice number is rejected by the app.

## 8. Milestones (commit after each; explain each one to Sam in plain English)

1. **The company** (~40 min): invoices generated, the Flask app runs, and a record can be entered by hand. *Done when* the list page shows a manually entered invoice.
2. **Hands** (~40 min): the browser wrapper and all tools work when called directly from a script, without the LLM. *Done when* a script fills and submits the form by labels.
3. **Brain + loop** (~60 min): the main Globex task completes live with Groq, including approval and verification. *Done when* `summary.md` shows ✅ verified.
4. **Reliability** (~40 min): the faults, the ambiguity case and the duplicate case all work. *Done when* tasks 4–7 pass live.
5. **Eval + demo** (~40 min): `results.md` from a live run, and `video.webm` of the main task with one injected failure. *Done when* both files exist.
6. **README** (~20 min): what it is; how to run it; an architecture diagram (ASCII is fine); design decisions; the results table; assumptions; known limitations; what next; models and tools used (including **Claude Code**).

If time runs out, stop after the last completed milestone. Milestones 1–3 alone are a legitimate submission. 4 and 5 are what make it stand out.

## 9. After each milestone: the "explain it to Sam" block

At the end of every milestone, write a short plain-English explanation (no jargon, or jargon explained):
- what was built and which file it's in
- **why** it's built that way
- one question an interviewer might ask about it, with the answer

At the end, also write `INTERVIEW_PREP.md` containing:
- the 3 core "why" answers: why a plain loop instead of a framework; how verification works and why through the UI; what happens when a step fails
- step-by-step instructions for 2 practice changes Sam will make himself:
  - (a) add a new tool, e.g. `browser_select` for dropdowns
  - (b) make approval required for "Mark as paid" too

---

## Kickoff prompt (paste into Claude Code)

> Read `TASK_WORKER_SPEC.md` and build it exactly in this repo. I'm not a strong coder and I'll have to explain and modify this system live in an interview, so keep everything small, plain Python and heavily commented, with no agent frameworks. Follow the milestones in order. After each milestone: run it, show me the evidence that its "done when" is met, commit with a clear message, and give me the plain-English "explain it to Sam" block from section 9. Never claim something works unless you ran it. Use the GROQ_API_KEY environment variable and never print it. Hard stop at 3:30 AM IST: if we're short on time, finish the current milestone cleanly and write the README for what actually works.
