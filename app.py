from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
from pathlib import Path
from datetime import date, datetime
from calendar import month_name

app = Flask(__name__)
app.secret_key = "replace-this-with-a-long-random-secret-before-deployment"
DB_PATH = Path("/tmp/monetra.db")

CATEGORIES = ["Продукты", "Транспорт", "Дом", "Рестораны", "Здоровье", "Развлечения", "Подписки", "Зарплата", "Фриланс", "Подарки", "Другое"]

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect_db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            tx_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_key TEXT NOT NULL,
            title TEXT NOT NULL,
            target REAL NOT NULL CHECK(target > 0),
            saved REAL NOT NULL DEFAULT 0 CHECK(saved >= 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")

def profile():
    key = session.get("user_key")
    if not key:
        return None
    return {"key": key, "first": session.get("first_name", ""), "last": session.get("last_name", "")}

def get_transactions(key):
    with connect_db() as conn:
        return conn.execute("SELECT * FROM transactions WHERE user_key=? ORDER BY tx_date DESC, id DESC", (key,)).fetchall()

def summary(rows):
    income = sum(float(r["amount"]) for r in rows if r["kind"] == "income")
    expenses = sum(float(r["amount"]) for r in rows if r["kind"] == "expense")
    return {"income": income, "expenses": expenses, "balance": income-expenses}

@app.template_filter("money")
def money_filter(value):
    try:
        return f"{float(value):,.2f}".replace(",", " ")
    except (ValueError, TypeError):
        return "0.00"

@app.template_filter("date_ru")
def date_ru(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return value

@app.context_processor
def inject_globals():
    return {"categories": CATEGORIES, "today_iso": date.today().isoformat()}

@app.route("/", methods=["GET", "POST"])
def welcome():
    if request.method == "POST":
        first = request.form.get("first_name", "").strip()
        last = request.form.get("last_name", "").strip()
        if not first or not last:
            return render_template("welcome.html", error="Заполни оба поля — имя и фамилию.")
        if len(first) > 50 or len(last) > 50:
            return render_template("welcome.html", error="Имя и фамилия должны быть не длиннее 50 символов.")
        if any(ch.isdigit() for ch in first + last):
            return render_template("welcome.html", error="В имени и фамилии не должно быть цифр.")
        session["first_name"] = first
        session["last_name"] = last
        # A lightweight local profile, not a secure account system.
        session["user_key"] = (first + " " + last).casefold()
        return redirect(url_for("dashboard"))
    if profile():
        return redirect(url_for("dashboard"))
    return render_template("welcome.html", error=None)

@app.post("/switch-user")
def switch_user():
    session.clear()
    return redirect(url_for("welcome"))

@app.route("/dashboard")
def dashboard():
    p = profile()
    if not p:
        return redirect(url_for("welcome"))
    rows = get_transactions(p["key"])
    totals = summary(rows)
    expense_categories = {}
    monthly = {}
    for row in rows:
        month = row["tx_date"][:7]
        bucket = monthly.setdefault(month, {"income": 0, "expense": 0})
        bucket[row["kind"]] += row["amount"]
        if row["kind"] == "expense":
            expense_categories[row["category"]] = expense_categories.get(row["category"], 0) + row["amount"]
    month_labels = sorted(monthly.keys())[-7:]
    month_income = [round(monthly[m]["income"], 2) for m in month_labels]
    month_expense = [round(monthly[m]["expense"], 2) for m in month_labels]
    category_labels = list(sorted(expense_categories, key=expense_categories.get, reverse=True))
    category_values = [round(expense_categories[k], 2) for k in category_labels]
    with connect_db() as conn:
        goals = conn.execute("SELECT * FROM goals WHERE user_key=? ORDER BY id DESC", (p["key"],)).fetchall()
    return render_template("dashboard.html", p=p, rows=rows, recent=rows[:6], goals=goals,
        totals=totals, month_labels=month_labels, month_income=month_income, month_expense=month_expense,
        category_labels=category_labels, category_values=category_values)

@app.route("/transactions")
def transactions_page():
    p = profile()
    if not p:
        return redirect(url_for("welcome"))
    rows = get_transactions(p["key"])
    return render_template("transactions.html", p=p, rows=rows)

@app.post("/transactions/add")
def add_transaction():
    p = profile()
    if not p:
        return redirect(url_for("welcome"))
    kind = request.form.get("kind", "")
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "Другое").strip()
    tx_date = request.form.get("tx_date", date.today().isoformat())
    try:
        amount = float(request.form.get("amount", "").replace(",", "."))
    except ValueError:
        amount = 0
    try:
        datetime.strptime(tx_date, "%Y-%m-%d")
    except ValueError:
        tx_date = date.today().isoformat()
    if kind not in ("income", "expense") or not title or amount <= 0:
        flash("Проверь название операции и сумму: сумма должна быть больше нуля.", "error")
        return redirect(request.referrer or url_for("dashboard"))
    if category not in CATEGORIES:
        category = "Другое"
    with connect_db() as conn:
        conn.execute("INSERT INTO transactions(user_key,kind,title,category,amount,tx_date) VALUES(?,?,?,?,?,?)",
            (p["key"], kind, title[:100], category, amount, tx_date))
    flash("Операция сохранена.", "success")
    return redirect(request.referrer or url_for("dashboard"))

@app.post("/transactions/<int:tx_id>/delete")
def delete_transaction(tx_id):
    p = profile()
    if not p:
        return redirect(url_for("welcome"))
    with connect_db() as conn:
        conn.execute("DELETE FROM transactions WHERE id=? AND user_key=?", (tx_id, p["key"]))
    flash("Операция удалена.", "success")
    return redirect(request.referrer or url_for("transactions_page"))

@app.post("/goals/add")
def add_goal():
    p = profile()
    if not p:
        return redirect(url_for("welcome"))
    title = request.form.get("title", "").strip()
    try:
        target = float(request.form.get("target", "").replace(",", "."))
        saved = float(request.form.get("saved", "0").replace(",", ".") or 0)
    except ValueError:
        target, saved = 0, 0
    if not title or target <= 0 or saved < 0:
        flash("Укажи название цели, положительную сумму и накопления не меньше нуля.", "error")
    else:
        with connect_db() as conn:
            conn.execute("INSERT INTO goals(user_key,title,target,saved) VALUES(?,?,?,?)",
                         (p["key"], title[:100], target, saved))
        flash("Цель добавлена.", "success")
    return redirect(url_for("dashboard") + "#goals")

@app.post("/goals/<int:goal_id>/delete")
def delete_goal(goal_id):
    p = profile()
    if not p:
        return redirect(url_for("welcome"))
    with connect_db() as conn:
        conn.execute("DELETE FROM goals WHERE id=? AND user_key=?", (goal_id, p["key"]))
    return redirect(url_for("dashboard") + "#goals")

@app.route("/analytics")
def analytics():
    p = profile()
    if not p:
        return redirect(url_for("welcome"))
    rows = get_transactions(p["key"])
    totals = summary(rows)
    cats = {}
    monthly = {}
    for row in rows:
        month = row["tx_date"][:7]
        bucket = monthly.setdefault(month, {"income": 0, "expense": 0})
        bucket[row["kind"]] += row["amount"]
        if row["kind"] == "expense":
            cats[row["category"]] = cats.get(row["category"], 0) + row["amount"]
    month_keys = sorted(monthly)
    return render_template("analytics.html", p=p, totals=totals,
        category_labels=list(cats.keys()), category_values=list(cats.values()),
        month_labels=month_keys, month_income=[monthly[m]["income"] for m in month_keys],
        month_expense=[monthly[m]["expense"] for m in month_keys], rows=rows)

@app.route("/settings")
def settings():
    p = profile()
    if not p:
        return redirect(url_for("welcome"))
    return render_template("settings.html", p=p)

@app.get("/api/summary")
def api_summary():
    p = profile()
    if not p:
        return jsonify({"error": "profile_required"}), 401
    return jsonify(summary(get_transactions(p["key"])))

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="Эта страница не найдена."), 404

init_db()
if __name__ == "__main__":
    app.run(debug=True)
