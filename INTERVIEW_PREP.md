# Interview prep

## The 3 core "why" answers

### 1. Why a plain loop instead of a framework (LangChain, CrewAI ...)?
- The whole agent is one `for` loop in `agent/loop.py`: **decide → act → observe → record**, repeated up to `MAX_STEPS`.
- I can explain every line, and debug it with a print statement. A framework hides the loop, the prompt and the retries.
- The safety rules (step limit, retry limit, approval gate) are a few `if` statements I can point at, not framework settings.
- Swapping the model is one line (`config.MODEL`), and tests use a fake model (`ScriptedLLM`) with the same `decide()` method.

### 2. How does verification work, and why through the UI?
- After submitting, the agent must open the list or detail page, `browser_read` it, and compare every value with what it read from the PDF (rule 8 in `agent/prompts.py`).
- `finish` has a separate `verified` flag; `summary.md` shows ✅ or ❌ for it.
- **Why the UI:** that's what a human checker would look at. A "200 OK" or "I clicked Submit" doesn't prove the record is right (the form could have rejected a field, saved a typo, or hit a 500).
- **And independently:** the eval never trusts the agent. `eval/run_eval.py` checks the SQLite database directly, and the agent never sees that checker.

### 3. What happens when a step fails?
1. Tools never crash the loop. Every error becomes an observation like `FAILED: ...` (`tools.execute`). An HTTP error page (400/500) also counts as a failure.
2. The LLM sees the failure in its history and should read the page and fix the cause (rule 7).
3. The loop counts failures of each *exact* action. After the first try plus 2 retries (`MAX_RETRIES`), the LLM gets a WARNING, and that same action is **blocked** from then on. That forces a different approach or `ask_human`.
4. If it never finishes, the loop stops at `MAX_STEPS` and reports **INCOMPLETE** honestly, with all evidence saved.

Example: with `FAIL_FIRST_SUBMIT`, Submit returns a 500 page → observation is FAILED → the agent reopens the form, refills it, asks for approval again and resubmits → the record exists exactly once.

---

## Practice change (a): add a `browser_select` tool for dropdowns

Goal: let the agent pick an option in a `<select>` by its label.

1. **`agent/browser.py`**: add a method to the `Browser` class:
   ```python
   def select(self, label, option):
       """Choose an option in a dropdown found by its visible label."""
       field = self.page.get_by_label(label, exact=True)
       if field.count() != 1:
           raise LookupError(f"No single dropdown labelled '{label}'.")
       field.select_option(label=option)
       return f"Selected '{option}' in '{label}'."
   ```
2. **`agent/tools.py`**: add the tool function next to `browser_fill`:
   ```python
   def browser_select(ctx, field_label, option):
       return ok(ctx.browser.select(field_label, option))
   ```
3. Still in `tools.py`, describe it for the LLM by adding to `SCHEMAS`:
   ```python
   _schema("browser_select", "Choose an option in a dropdown, found by its visible label.",
           field_label=("string", "The dropdown label as shown by browser_read."),
           option=("string", "The visible text of the option to choose.")),
   ```
4. And register it: add `browser_select` to the list inside `FUNCTIONS = {...}`.
5. Done. The loop needs no change: it sends every schema in `SCHEMAS` to the LLM and runs anything in `FUNCTIONS`. Screenshots happen automatically because the name starts with `browser_`.
6. To try it: add a `<select>` to `company/templates/new.html`, e.g. a "Currency" dropdown, then run `python -m pytest`.

## Practice change (b): require approval for "Mark as paid" too

1. Open **`config.py`**.
2. Change
   ```python
   NEEDS_APPROVAL = ["Submit"]
   ```
   to
   ```python
   NEEDS_APPROVAL = ["Submit", "Mark as paid"]
   ```
3. Done. `browser_click` in `agent/tools.py` checks this list: a click on any button in it is BLOCKED unless `request_approval` was approved just before, and each approval is used up by one click.
4. To prove it, copy `test_submit_without_approval_is_blocked` in `tests/test_loop.py`: seed one invoice with `company_app.add_invoice(...)`, open `/invoices/1`, click "Mark as paid" without approval, and assert the observation starts with `BLOCKED` and the status is still `Unpaid`.
