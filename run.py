"""Command line entry point.

    python run.py "Find the latest invoice from Globex, ... and tell me once it's done."
    python run.py "..." --auto-approve --video --fault FAIL_FIRST_SUBMIT

It starts the company app, opens a browser, runs the agent loop and saves
evidence to runs/<timestamp>/.
"""
import argparse
from datetime import datetime

from agent.browser import Browser
from agent.llm import GroqLLM
from agent.loop import run_agent
from agent.memory import RunState
from agent.tools import ToolContext
from company import app as company_app
from company import faults, make_invoices
from config import APP_URL, INBOX_DIR, RUNS_DIR


def cli_ask(question):
    return input(f"\n🤖 Agent asks: {question}\n> ")


def cli_approve(summary):
    return input(f"\n🤖 Agent wants to: {summary}\nApprove? [y/N] ").strip().lower() in ("y", "yes")


def run_task(goal, llm, ask_human, approve, video=False, name=""):
    """Run one task end to end and return (state, run_dir). Shared by run.py and the eval."""
    run_dir = RUNS_DIR / (datetime.now().strftime("%Y%m%d-%H%M%S") + (f"-{name}" if name else ""))
    run_dir.mkdir(parents=True, exist_ok=True)
    browser = Browser(APP_URL, video_dir=run_dir if video else None)
    try:
        ctx = ToolContext(browser, RunState(goal), ask_human, approve)
        state = run_agent(llm, ctx, run_dir)
    finally:
        video_file = browser.page.video.path() if video else None
        browser.close()  # the video file is only complete after closing
        if video_file:
            (run_dir / video_file.split("/")[-1]).rename(run_dir / "video.webm")
    return state, run_dir


def main():
    parser = argparse.ArgumentParser(description="Autonomous AI task worker")
    parser.add_argument("task", help="The task in plain English, in quotes")
    parser.add_argument("--auto-approve", action="store_true", help="Approve every request automatically")
    parser.add_argument("--video", action="store_true", help="Record a video of the browser")
    parser.add_argument("--fault", action="append", default=[], choices=list(faults.FAULTS),
                        help="Inject a failure (can be repeated)")
    args = parser.parse_args()

    if not any(INBOX_DIR.glob("*.pdf")):
        make_invoices.main()
    faults.reset(**{name: True for name in args.fault})
    server = company_app.start_in_background()
    approve = (lambda summary: print(f"\n(auto-approved) {summary}") or True) if args.auto_approve else cli_approve

    state, run_dir = run_task(args.task, GroqLLM(), cli_ask, approve, video=args.video)
    server.shutdown()
    print("\n" + (run_dir / "summary.md").read_text())
    print(f"Evidence saved in {run_dir}")


if __name__ == "__main__":
    main()
