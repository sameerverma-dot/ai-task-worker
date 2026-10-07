"""Failure injection: switches that make the company app misbehave on purpose.

Turn them on with env vars (FAIL_FIRST_SUBMIT=1 ...) or run.py flags.
The eval sets FAULTS directly between tasks.
"""
import os
import random
import time

FAULTS = {
    "FAIL_FIRST_SUBMIT": os.environ.get("FAIL_FIRST_SUBMIT") == "1",  # first submit -> 500 error
    "RENAME_FIELD": os.environ.get("RENAME_FIELD") == "1",            # "Due Date" label -> "Payment Due"
    "SLOW_PAGE": os.environ.get("SLOW_PAGE") == "1",                  # random 1-3 s delay per page
}

# Remembers whether FAIL_FIRST_SUBMIT has already fired, so it fails only once.
_already_failed = {"submit": False}


def reset(**switches):
    """Turn all faults off, then turn on the ones given, e.g. reset(RENAME_FIELD=True)."""
    for name in FAULTS:
        FAULTS[name] = bool(switches.get(name, False))
    _already_failed["submit"] = False


def should_fail_submit():
    if FAULTS["FAIL_FIRST_SUBMIT"] and not _already_failed["submit"]:
        _already_failed["submit"] = True
        return True
    return False


def due_date_label():
    return "Payment Due" if FAULTS["RENAME_FIELD"] else "Due Date"


def maybe_slow_down():
    if FAULTS["SLOW_PAGE"]:
        time.sleep(random.uniform(1, 3))
