"""Replay a logged run on video, without calling the LLM.

    python -m eval.replay_run runs/<run-folder> [--fault FAIL_FIRST_SUBMIT]

The decisions are read from that run's steps.jsonl and fed back through the real loop
(ScriptedLLM). The browser, app, faults, approval gate and verification all run for real;
only the "brain" is a recording. Useful for demos when the API quota is used up.
"""
import json
import sys
import time
from pathlib import Path

from agent.llm import ScriptedLLM
from company import app as company_app
from company import faults
from run import run_task


class PacedLLM(ScriptedLLM):
    """Same recorded decisions, with a pause before each, so the video is watchable."""
    def decide(self, system, user, tools):
        time.sleep(2)
        return super().decide(system, user, tools)


def main():
    source = Path(sys.argv[1])
    switches = sys.argv[sys.argv.index("--fault") + 1:] if "--fault" in sys.argv else []
    steps = [json.loads(line) for line in open(source / "steps.jsonl")]
    llm = PacedLLM([(s["tool"], s["args"]) for s in steps])

    company_app.init_db(reset=True)
    faults.reset(**{name: True for name in switches})
    server = company_app.start_in_background()
    goal = f"REPLAY of {source.name} (recorded decisions, no live LLM)"
    state, run_dir = run_task(goal, llm, ask_human=lambda q: "replay", approve=lambda s: True,
                              video=True, name="replay")
    server.shutdown()
    print(f"\nReplayed {len(steps)} steps. Invoices in the app now: {company_app.all_invoices()}")
    print(f"Video: {run_dir / 'video.webm'}")


if __name__ == "__main__":
    main()
