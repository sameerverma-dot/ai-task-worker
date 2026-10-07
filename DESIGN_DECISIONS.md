# Design decisions

The reasoning behind the three choices that shape this project most.

## 1. A plain loop instead of an agent framework

The agent is one `for` loop in `agent/loop.py`: **decide → act → observe → record**, repeated up to `MAX_STEPS`.

- **Readable and debuggable.** Every step of the control flow is visible in about 90 lines. A print statement is enough to debug it. Frameworks such as LangChain or CrewAI hide the loop, the prompt and the retry policy behind their own abstractions.
- **Safety rules are code, not settings.** The step limit, the retry limit and the approval gate are plain `if` statements, so it's easy to point at exactly where each one is enforced.
- **The model is swappable.** Anything with a `decide()` method works: `GroqLLM` for real runs, `ScriptedLLM` for offline tests. Changing the model is one line in `config.py`.

## 2. Verification through the UI, checked independently

- After making a change, the agent must open the list or detail page, read it with `browser_read`, and compare every value with what it extracted from the source document (rule 8 in `agent/prompts.py`).
- `finish` has a separate `verified` flag, shown as ✅/❌ in each run's `summary.md`.
- **Why the UI:** it's what a human checker would look at. A successful HTTP response or a completed click doesn't prove the record is right: the form may have rejected a field, stored a typo, or returned an error page.
- **Independent check:** the eval doesn't trust the agent's report. `eval/run_eval.py` inspects the SQLite database directly, with expectations the agent never sees.

## 3. What happens when a step fails

1. **Tools never crash the loop.** Every exception becomes an observation like `FAILED: ...` (`tools.execute`). HTTP error pages (4xx/5xx) also count as failures, so a 500 is never mistaken for success.
2. **The model sees the failure** in its history and is told to read the page, understand the cause and fix it (rule 7).
3. **Repeated failures are capped.** The loop counts how many times in a row each exact action has failed. After the original attempt plus `MAX_RETRIES` (2) retries, the model gets a warning, and further repeats of that action are blocked. That forces a different approach or a question to the human. Any successful step restarts the count, because the situation has changed; otherwise a problem that was fixed (say, a refilled form) would keep a button blocked for the rest of the run.
4. **Honest stop.** If the agent never calls `finish`, the loop stops at `MAX_STEPS` and reports **INCOMPLETE**, with all evidence saved.

Example: with the `FAIL_FIRST_SUBMIT` fault, the first Submit returns a 500 page and is recorded as a failure. The agent then returns to the form, refills it, requests approval again and resubmits. The record ends up existing exactly once.
