"""Run state: everything the agent has learned and done during one run.

The LLM has no memory of its own between calls. Each step we rebuild its
view of the world from this object: the goal, the facts found so far and
a condensed history of the steps.
"""
import json
from collections import Counter

from config import HISTORY_FULL_STEPS


class RunState:
    def __init__(self, goal):
        self.goal = goal
        self.facts = {}           # e.g. {"Globex_GLX-1032.pdf": "<text of that invoice>"}
        self.steps = []           # one dict per step: thought, tool, args, ok, observation, seconds
        self.failures = Counter() # how many times each exact action has failed
        self.approved = False     # set by request_approval; used up by the next guarded click
        self.final = None         # set by the finish tool

    def record(self, step):
        self.steps.append(step)

    @staticmethod
    def action_key(tool, args):
        """A stable name for 'this exact action', used to count repeated failures."""
        return f"{tool}({json.dumps(args, sort_keys=True)})"

    def history_text(self):
        """Last few steps in full; older ones squeezed to one line each to keep the prompt small."""
        if not self.steps:
            return "(no steps yet)"
        lines = []
        cutoff = len(self.steps) - HISTORY_FULL_STEPS
        for i, s in enumerate(self.steps, start=1):
            status = "OK" if s["ok"] else "FAILED"
            if i <= cutoff:
                lines.append(f"Step {i}: {s['tool']}({s['args']}) -> {status}: {s['observation'][:80]}")
            else:
                lines.append(f"Step {i}: thought: {s['thought']}\n  action: {s['tool']}({s['args']})"
                             f"\n  result ({status}): {s['observation']}")
        return "\n".join(lines)

    def prompt_text(self, warning=None):
        """The user message the LLM sees at each step."""
        facts = "\n\n".join(f"--- {name} ---\n{text}" for name, text in self.facts.items()) or "(none yet)"
        text = (f"GOAL: {self.goal}\n\n"
                f"DOCUMENTS READ SO FAR:\n{facts}\n\n"
                f"STEPS SO FAR:\n{self.history_text()}\n\n"
                f"Approval currently granted: {self.approved}\n"
                "Choose the next tool call.")
        if warning:
            text += f"\n\nWARNING: {warning}"
        return text
