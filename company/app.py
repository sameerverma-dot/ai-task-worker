""""Acme Accounts": the small internal web app the agent works in.

Run on its own:  python -m company.app   then open http://127.0.0.1:5055/invoices
run.py and the eval start it automatically in a background thread.
"""
import re
import sqlite3
import threading

from flask import Flask, redirect, render_template, request
from werkzeug.serving import make_server

from company import faults
from config import APP_PORT, DB_PATH

app = Flask(__name__)


# ---------- database ----------

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(reset=False):
    """Create the table. reset=True wipes all data first (used by tests and eval)."""
    with db() as conn:
        if reset:
            conn.execute("DROP TABLE IF EXISTS invoices")
        conn.execute("""CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT NOT NULL,
            number TEXT NOT NULL UNIQUE,
            amount REAL NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Unpaid')""")


def add_invoice(vendor, number, amount, due_date, status="Unpaid"):
    with db() as conn:
        conn.execute("INSERT INTO invoices (vendor, number, amount, due_date, status) VALUES (?,?,?,?,?)",
                     (vendor, number, amount, due_date, status))


def all_invoices():
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM invoices ORDER BY id")]


# ---------- pages ----------

@app.before_request
def slow_down():
    faults.maybe_slow_down()


@app.route("/")
def home():
    return redirect("/invoices")


@app.route("/invoices")
def list_invoices():
    return render_template("list.html", invoices=all_invoices())


@app.route("/invoices/new", methods=["GET", "POST"])
def new_invoice():
    form = request.form
    error = None
    if request.method == "POST":
        if faults.should_fail_submit():
            return render_template("error.html"), 500

        # Validate like a real system would, with visible error messages.
        vendor = form.get("vendor", "").strip()
        number = form.get("number", "").strip()
        due = form.get("due_date", "").strip()
        try:
            amount = float(form.get("amount", "").replace(",", "").strip())
        except ValueError:
            amount = None
        if not (vendor and number and due) or amount is None:
            error = "All fields are required and Amount must be a number."
        elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due):
            error = "Due date must be in YYYY-MM-DD format."
        else:
            try:
                add_invoice(vendor, number, amount, due)
                new_id = db().execute("SELECT id FROM invoices WHERE number=?", (number,)).fetchone()[0]
                return redirect(f"/invoices/{new_id}?saved=1")
            except sqlite3.IntegrityError:
                error = f"Duplicate invoice: invoice number {number} already exists."
    return render_template("new.html", error=error, form=form,
                           due_label=faults.due_date_label()), (400 if error else 200)


@app.route("/invoices/<int:inv_id>")
def invoice_detail(inv_id):
    row = db().execute("SELECT * FROM invoices WHERE id=?", (inv_id,)).fetchone()
    if row is None:
        return "Invoice not found", 404
    return render_template("detail.html", inv=row, saved=request.args.get("saved"))


@app.route("/invoices/<int:inv_id>/pay", methods=["POST"])
def mark_paid(inv_id):
    with db() as conn:
        conn.execute("UPDATE invoices SET status='Paid' WHERE id=?", (inv_id,))
    return redirect(f"/invoices/{inv_id}")


# ---------- running ----------

def start_in_background():
    """Start the app in a background thread (used by run.py, eval and tests)."""
    init_db()
    server = make_server("127.0.0.1", APP_PORT, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    init_db()
    app.run(port=APP_PORT)
