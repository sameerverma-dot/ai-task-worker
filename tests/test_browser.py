import pytest

from company import faults


def test_fill_by_label(browser):
    browser.open("/invoices/new")
    browser.fill("Due Date", "2026-10-20")
    assert browser.page.get_by_label("Due Date").input_value() == "2026-10-20"


def test_field_found_by_reading_after_rename(browser):
    faults.reset(RENAME_FIELD=True)
    browser.open("/invoices/new")
    with pytest.raises(LookupError) as err:      # the old label is gone...
        browser.fill("Due Date", "2026-10-20")
    assert "Payment Due" in str(err.value)       # ...and the error tells you the real labels
    assert "'Payment Due'" in browser.read()     # reading the page shows the new label
    browser.fill("Payment Due", "2026-10-20")    # filling by the new label works
    assert browser.page.get_by_label("Payment Due").input_value() == "2026-10-20"
