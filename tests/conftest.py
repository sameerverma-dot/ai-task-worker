"""Shared test setup. Tests run offline: the company app runs locally and the LLM is scripted."""
import os
import sys
import tempfile
from pathlib import Path

# Own port and database, so tests never touch a real run. Must be set before config is imported.
os.environ["APP_PORT"] = "5077"
os.environ["ACME_DB"] = str(Path(tempfile.mkdtemp()) / "test.db")
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest  # noqa: E402

from agent.browser import Browser  # noqa: E402
from company import app as company_app  # noqa: E402
from company import faults, make_invoices  # noqa: E402
from config import APP_URL, INBOX_DIR  # noqa: E402


@pytest.fixture(scope="session")
def server():
    if not any(INBOX_DIR.glob("*.pdf")):
        make_invoices.main()
    srv = company_app.start_in_background()
    yield srv
    srv.shutdown()


@pytest.fixture
def browser(server):
    company_app.init_db(reset=True)
    faults.reset()
    b = Browser(APP_URL)
    yield b
    b.close()
    faults.reset()
