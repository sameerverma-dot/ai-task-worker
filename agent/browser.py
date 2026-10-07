"""A thin wrapper around Playwright (a library that drives a real Chromium browser).

Everything works by what a human sees: field LABELS and button TEXT,
never by CSS selectors. That's why a renamed field doesn't break the agent:
it reads the page, sees the new label, and uses it.
"""
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

# JavaScript run inside the page: list every visible form field with its label.
FIELDS_JS = """() => Array.from(document.querySelectorAll('input, select, textarea'))
  .filter(e => e.type !== 'hidden')
  .map(e => {
    const label = e.id ? document.querySelector(`label[for="${e.id}"]`) : null;
    return {label: label ? label.innerText.trim() : (e.getAttribute('aria-label') || e.name),
            value: e.value, placeholder: e.placeholder || ''};
  })"""

CLICKABLES_JS = """() => ({
  buttons: Array.from(document.querySelectorAll('button, input[type=submit]'))
             .map(e => (e.innerText || e.value).trim()),
  links: Array.from(document.querySelectorAll('a')).map(e => e.innerText.trim())})"""


class Browser:
    def __init__(self, base_url, video_dir=None, headless=True):
        self.base_url = base_url
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=headless)
        self._context = self._browser.new_context(record_video_dir=str(video_dir) if video_dir else None)
        self.page = self._context.new_page()
        # Generous timeout so slow pages (SLOW_PAGE fault) are waited for, not failed.
        self.page.set_default_timeout(15000)
        self.last_status = 200  # HTTP status of the last page load (500 = server error)

    def open(self, path):
        """Go to a page of the app, e.g. '/invoices/new'. Waits until it has fully loaded."""
        response = self.page.goto(self.base_url + path, wait_until="load")
        return self._where(response)

    def read(self):
        """Return what a person would see: the page text, the form fields and the buttons/links."""
        fields = self.page.evaluate(FIELDS_JS)
        clickables = self.page.evaluate(CLICKABLES_JS)
        lines = [f"URL: {self.page.url}", f"TITLE: {self.page.title()}",
                 "TEXT:", self.page.inner_text("body")[:1500], "FORM FIELDS:"]
        lines += [f"  - '{f['label']}' (current value: '{f['value']}', hint: '{f['placeholder']}')"
                  for f in fields] or ["  (none)"]
        lines.append(f"BUTTONS: {clickables['buttons']}")
        lines.append(f"LINKS: {clickables['links']}")
        return "\n".join(lines)

    def fill(self, label, value):
        """Type a value into the field whose visible label is `label`."""
        field = self.page.get_by_label(label, exact=True)
        if field.count() == 0:  # allow small differences like 'Due date' vs 'Due Date'
            field = self.page.get_by_label(label, exact=False)
        if field.count() != 1:
            labels = [f["label"] for f in self.page.evaluate(FIELDS_JS)]
            raise LookupError(f"No single field labelled '{label}'. Fields on this page: {labels}")
        field.fill(str(value))
        return f"Filled '{label}' with '{value}'."

    def click(self, text):
        """Click a button (or, failing that, a link) by its visible text, then wait for the page."""
        target = None
        for candidate in (self.page.get_by_role("button", name=text, exact=True),
                          self.page.get_by_role("link", name=text, exact=True),
                          self.page.get_by_role("button", name=text),
                          self.page.get_by_role("link", name=text)):
            if candidate.count() > 0:
                target = candidate.first
                break
        if target is None:
            raise LookupError(f"Nothing clickable with text '{text}'. "
                              f"Page has: {self.page.evaluate(CLICKABLES_JS)}")
        try:
            # Most clicks here load a new page; wait for it (handles slow pages).
            with self.page.expect_navigation(wait_until="load", timeout=10000) as nav:
                target.click()
            return f"Clicked '{text}'. " + self._where(nav.value)
        except PlaywrightTimeout:
            return f"Clicked '{text}' (page did not change). " + self._where(None)

    def screenshot(self, path):
        self.page.screenshot(path=str(path), full_page=True)
        return path

    def close(self):
        self._context.close()  # closing the context is what saves the video file
        self._browser.close()
        self._pw.stop()

    def _where(self, response):
        """Short description of where we ended up, including the HTTP status (500 = server error)."""
        status = response.status if response else "?"
        self.last_status = response.status if response else 200
        return f"Now on {self.page.url} (HTTP {status}, title: '{self.page.title()}')."
