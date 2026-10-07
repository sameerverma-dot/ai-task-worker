# Eval results

Live run on Groq (free tier). Success rate: **3/3 (100%)**

Time includes waiting for Groq's free-tier rate limit (8k tokens/min). When a model's daily token quota ran out, the agent switched to the next model, so the model is listed per task.

| # | Task | Result | Steps | Time (s) | Reason | Model(s) | Run folder |
|---|---|---|---|---|---|---|---|
| 1 | main Globex task | ✅ pass | 16 | 313 | ok | openai/gpt-oss-120b, qwen/qwen3.8-27b | `runs/20261007-175600-eval1` |
| 2 | all unpaid Initech | ✅ pass | 27 | 714 | ok | qwen/qwen3.8-27b | `runs/20261007-180113-eval2` |
| 3 | mark Umbrella paid | ✅ pass | 8 | 162 | ok | qwen/qwen3.8-27b | `runs/20261007-181307-eval3` |
