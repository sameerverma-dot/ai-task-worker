"""All settings in one place, so changing behaviour never means hunting through code."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# --- LLM ---
# The key is read by llm.py from the GROQ_API_KEY env var. It is never stored here.
# llama-3.3-70b-versatile (the spec default) is no longer offered by Groq; gpt-oss-120b does tool calling well.
MODEL = os.environ.get("MODEL", "openai/gpt-oss-120b")
# Groq's free tier also caps tokens PER DAY for each model. When one model's daily quota is used up,
# GroqLLM switches to the next model in this list (and logs which model made each decision).
FALLBACK_MODELS = ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]

# --- Agent loop ---
MAX_STEPS = 40          # hard cap so a confused agent can never run forever (spec said 25; too tight
                        # for multi-invoice tasks, since each field is filled in its own step)
MAX_RETRIES = 2         # after this many retries of the same failing action, force a new approach
HISTORY_FULL_STEPS = 5  # the last N steps go to the LLM in full; older ones as one-line summaries

# Buttons that change data for real. browser_click refuses them until
# request_approval was called and approved. Add "Mark as paid" here to guard that too.
NEEDS_APPROVAL = ["Submit"]

# --- The simulated company ---
APP_PORT = int(os.environ.get("APP_PORT", "5055"))
APP_URL = f"http://127.0.0.1:{APP_PORT}"
DB_PATH = Path(os.environ.get("ACME_DB", BASE_DIR / "company" / "acme.db"))
INBOX_DIR = BASE_DIR / "company" / "inbox"
RUNS_DIR = BASE_DIR / "runs"
