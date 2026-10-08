# Eval results

Model(s): `qwen/qwen3.8-27b` (live, Groq free tier). Success rate: **2/2 (100%)**

Time is wall-clock and includes waiting for Groq's rate limits (and any pause for the daily token quota to come back), so it says more about the free tier than about the agent.

| # | Task | Result | Steps | Time (s) | Reason | Model | Run folder |
|---|---|---|---|---|---|---|---|
| 8 | read-only question | ✅ pass | 13 | 282 | ok | qwen/qwen3.8-27b | `runs/20261008-044029-eval8` |
| 9 | impossible task (email) | ✅ pass | 1 | 13 | ok | qwen/qwen3.8-27b | `runs/20261008-044511-eval9` |
