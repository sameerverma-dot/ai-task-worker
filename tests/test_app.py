from company import app as company_app


def test_duplicate_invoice_number_is_rejected(server):
    company_app.init_db(reset=True)
    client = company_app.app.test_client()
    data = {"vendor": "Globex", "number": "GLX-1032", "amount": "78250.00", "due_date": "2026-10-20"}
    assert client.post("/invoices/new", data=data).status_code == 302  # saved, redirected to detail
    second = client.post("/invoices/new", data=data)
    assert second.status_code == 400
    assert b"Duplicate invoice" in second.data
    assert len(company_app.all_invoices()) == 1
