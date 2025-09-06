import json
from datetime import datetime, timedelta, date
import calendar
from flask import Flask, render_template, request, make_response, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from weasyprint import HTML

# ---------- APP SETUP ----------
app = Flask(__name__)
app.secret_key = "supersecret"  # Change in production

# ---------- DATA STORAGE ----------
DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": [], "tasks": [], "deadlines": [], "schedules": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------- AUTH ROUTES ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        data = load_data()
        user = next((u for u in data["users"] if u["email"] == email), None)
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            return redirect(url_for("index"))
        else:
            return "Invalid credentials!"
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = load_data()
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        if any(u["email"] == email for u in data["users"]):
            return "Email already registered!"
        user_id = len(data["users"]) + 1
        data["users"].append({
            "id": user_id,
            "name": name,
            "email": email,
            "password": password
        })
        save_data(data)
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------- HOME ----------
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    data = load_data()
    user_tasks = [t for t in data["tasks"] if t["user_id"] == session["user_id"]]
    user_deadlines = [d for d in data["deadlines"] if d["user_id"] == session["user_id"]]
    return render_template("index.html", name=session["name"], tasks=user_tasks, deadlines=user_deadlines)

# ---------- TIMETABLE ----------
@app.route("/timetable")
def timetable():
    if "user_id" not in session:
        return redirect(url_for("login"))
    today = datetime.today().date()
    data = load_data()
    current_user = next((u for u in data.get("users", []) if u["id"] == session["user_id"]), None)
    all_deadlines = []
    for d in data.get("deadlines", []):
        if d["user_id"] == session["user_id"]:
            try:
                due_date = datetime.strptime(d["due_date"], "%Y-%m-%d").date()
                days_left = (due_date - today).days
                all_deadlines.append({
                    "subject": d["subject"],
                    "due_date": due_date,
                    "days_left": days_left
                })
            except:
                continue
    daily_deadlines = [d for d in all_deadlines if d["due_date"] == today]
    weekly_deadlines = [d for d in all_deadlines if 0 <= d["days_left"] <= 7]
    monthly_deadlines = [d for d in all_deadlines if d["due_date"].month == today.month and d["due_date"].year == today.year]
    daily_schedules = [s for s in data.get("schedules", []) if s["user_id"] == session["user_id"] and s.get("day") == today.strftime("%Y-%m-%d")]
    return render_template("timetable.html",
                           user=current_user,
                           today=today,
                           daily_deadlines=daily_deadlines,
                           weekly_deadlines=weekly_deadlines,
                           monthly_deadlines=monthly_deadlines,
                           daily_schedules=daily_schedules)

# ---------- PDF GENERATION ----------
@app.route("/generate-pdf", methods=["POST"])
def generate_pdf():
    try:
        data = request.get_json()
        html_content = data.get("html_content", "")
        mode = data.get("mode", "daily")
        if not html_content:
            return "HTML content missing", 400

        # Generate PDF using WeasyPrint
        pdf_file = HTML(string=html_content).write_pdf()

        response = make_response(pdf_file)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=timetable_{mode}.pdf'
        return response
    except Exception as e:
        return f"Error generating PDF: {e}", 500

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
