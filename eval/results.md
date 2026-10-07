# Eval results

Model: `openai/gpt-oss-120b` (live, Groq). Success rate: **4/4 (100%)**

Time includes waiting for Groq's free-tier rate limit (8k tokens/min).

| # | Task | Result | Steps | Time (s) | Reason | Run folder |
|---|---|---|---|---|---|---|
| 4 | ambiguous Acme | ✅ pass | 18 | 202 | ok | `runs/20261007-173051-eval4` |
| 5 | main + FAIL_FIRST_SUBMIT | ✅ pass | 27 | 367 | ok | `runs/20261007-173412-eval5` |
| 6 | main + RENAME_FIELD + SLOW_PAGE | ✅ pass | 22 | 158 | ok | `runs/20261007-174019-eval6` |
| 7 | already entered (duplicate) | ✅ pass | 12 | 77 | ok | `runs/20261007-174258-eval7` |
