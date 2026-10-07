"""All settings in one place, so changing behaviour never means hunting through code."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# --- LLM ---
# The key is read by llm.py from the GROQ_API_KEY env var. It is never stored here.
MODEL = os.environ.get("MODEL", "llama-3.3-70b-versatile")

# --- Agent loop ---
MAX_STEPS = 25          # hard cap so a confused agent can never run forever
MAX_RETRIES = 2         # after this many retries of the same failing action, force a new approach
HISTORY_FULL_STEPS = 8  # the last N steps go to the LLM in full; older ones as one-line summaries

# Buttons that change data for real. browser_click refuses them until
# request_approval was called and approved. Add "Mark as paid" here to guard that too.
NEEDS_APPROVAL = ["Submit"]

# --- The simulated company ---
APP_PORT = int(os.environ.get("APP_PORT", "5055"))
APP_URL = f"http://127.0.0.1:{APP_PORT}"
DB_PATH = BASE_DIR / "company" / "acme.db"
INBOX_DIR = BASE_DIR / "company" / "inbox"
RUNS_DIR = BASE_DIR / "runs"
