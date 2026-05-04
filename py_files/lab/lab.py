from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3
import random
from datetime import date
import os

lab_bp = Blueprint(
    'lab',
    __name__,
    template_folder='templates',
    static_folder='static'
)

# ---------------- DB SETUP ----------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "hospital.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    return conn


def generate_lab_id(cursor):
    while True:
        lab_id = "L" + str(random.randint(100, 999))
        cursor.execute("SELECT labId FROM lab WHERE labId = ?", (lab_id,))
        if not cursor.fetchone():
            return lab_id


# ---------------- HOME ----------------

@lab_bp.route("/")
def home():
    return render_template("loginlab.html")


# ---------------- LOGIN ----------------

@lab_bp.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in go dashboard
    if "lab" in session:
        return redirect(url_for("lab.dashboard"))

    if request.method == "POST":
        lab_id = request.form.get("labId", "").strip()

        if not lab_id:
            return render_template("loginlab.html", error="Please enter Lab ID")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT labId FROM lab WHERE labId = ?", (lab_id,))
        lab = cursor.fetchone()
        conn.close()

        if not lab:
            return render_template("loginlab.html", error="Invalid Lab ID. Please try again.")

        # Store session
        session["lab"] = {"labId": lab["labId"]}

        return redirect(url_for("lab.dashboard"))

    return render_template("loginlab.html")


# ---------------- SIGNUP ----------------

@lab_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()

        lab_id = generate_lab_id(cursor)

        try:
            cursor.execute("""
                INSERT INTO lab (labId, patientId, testName, doctorId, reportBlob, result, date)
                VALUES (?, NULL, NULL, NULL, NULL, NULL, NULL)
            """, (lab_id,))
            conn.commit()

            print("GENERATED LAB ID:", lab_id)  # DEBUG

            return render_template("signuplab.html", lab_id=lab_id)

        except Exception as e:
            return render_template("signuplab.html", error=str(e))

        finally:
            conn.close()

    return render_template("signuplab.html")
# ---------------- DASHBOARD ----------------

@lab_bp.route("/dashboard")
def dashboard():
    if "lab" not in session:
        return redirect(url_for("lab.login"))

    today = date.today().strftime("%Y-%m-%d")

    return render_template(
        "dashboardlab.html",
        lab=session["lab"],
        today=today
    )


# ---------------- ADD REPORT ----------------

@lab_bp.route("/add_report", methods=["POST"])
def add_report():
    if "lab" not in session:
        return redirect(url_for("lab.login"))

    lab_id = session["lab"]["labId"]

    patient_id = request.form.get("patientId", "").strip()
    test_name = request.form.get("testName", "").strip()
    result = request.form.get("result", "").strip()
    entry_date = request.form.get("date", "").strip()

    if not entry_date:
        entry_date = date.today().strftime("%Y-%m-%d")

    report_file = request.files.get("reportFile")
    file_data = None

    if report_file and report_file.filename != "":
        file_data = report_file.read()

    today = date.today().strftime("%Y-%m-%d")

    if not file_data:
        return render_template(
            "dashboardlab.html",
            lab=session["lab"],
            error="A report file is required.",
            today=today
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """INSERT INTO lab (labId, patientId, testName, reportBlob, result, date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (lab_id, patient_id, test_name, file_data, result, entry_date)
        )

        conn.commit()

        return render_template(
            "dashboardlab.html",
            lab=session["lab"],
            success=f"Report for Patient {patient_id} added successfully!",
            today=today
        )

    except sqlite3.Error as e:
        return render_template(
            "dashboardlab.html",
            lab=session["lab"],
            error=f"Database error: {e}",
            today=today
        )

    finally:
        conn.close()


# ---------------- LOGOUT ----------------

@lab_bp.route("/logout")
def logout():
    session.pop("lab", None)
    return redirect(url_for("lab.login"))