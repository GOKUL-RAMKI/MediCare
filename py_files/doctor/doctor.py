from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3
import uuid
from datetime import date
import os

doctor_bp = Blueprint(
    'doctor',
    __name__,
    template_folder='templates',
    static_folder='static'
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "hospital.db")



def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



@doctor_bp.route("/")
def index():
    return render_template("logindoc.html")



@doctor_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        doctor_id = request.form.get("doctorId")
        password = request.form.get("password")

        conn = get_db()
        c = conn.cursor()

        c.execute(
            "SELECT * FROM doctor WHERE doctorId=? AND password=?",
            (doctor_id, password)
        )
        doc = c.fetchone()
        conn.close()

        if not doc:
            return render_template("logindoc.html", error="Invalid ID or password")

        session["doctor"] = dict(doc)
        return redirect(url_for("doctor.dashboard"))

    return render_template("logindoc.html")



@doctor_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = request.form
        
        conn = get_db()
        c = conn.cursor()
        
        # Generate a unique doctor ID
        doctor_id = "D" + str(uuid.uuid4())[:6].upper()
        while True:
            c.execute("SELECT doctorId FROM doctor WHERE doctorId=?", (doctor_id,))
            if c.fetchone() is None:
                break
            doctor_id = "D" + str(uuid.uuid4())[:6].upper()

        try:
            c.execute("""
                INSERT INTO doctor 
                (doctorId, doctorName, age, gender, dept, speciality, password)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                doctor_id,
                data.get("name"),
                int(data.get("age")),
                data.get("gender"),
                data.get("dept"),
                data.get("speciality"),
                data.get("password")
            ))

            conn.commit()

            return render_template("signupdoc.html", success=doctor_id)

        except Exception as e:
            return render_template("signupdoc.html", error=str(e))

        finally:
            conn.close()

    return render_template("signupdoc.html")



@doctor_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("doctor.login"))



@doctor_bp.route("/dashboard")
def dashboard():
    if "doctor" not in session:
        return redirect(url_for("doctor.login"))

    doc = session["doctor"]

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT w.*, p.name 
        FROM waitingList w
        JOIN patient p ON w.patientId = p.patientId
        WHERE w.status=0 AND w.preferredDoctor=?
    """, (doc["doctorId"],))
    preferred = c.fetchall()

    c.execute("""
        SELECT w.*, p.name 
        FROM waitingList w
        JOIN patient p ON w.patientId = p.patientId
        WHERE w.status=2 AND w.dept=?
    """, (doc["dept"],))
    others = c.fetchall()

    c.execute("""
        SELECT a.*, p.name 
        FROM assigned a
        JOIN patient p ON a.patientId = p.patientId
        WHERE a.doctorId=?
    """, (doc["doctorId"],))
    my_appts = c.fetchall()

    view = request.args.get("view", "appointments")
    search = request.args.get("search")
    records = []

    if view == "records" and search:
        c.execute("""
        SELECT c.*, p.name
        FROM consultation c
        JOIN patient p ON c.patientId = p.patientId
        WHERE c.patientId=?
        """, (search,))
        records = c.fetchall()

    conn.close()

    return render_template("dashboarddoc.html",
        doctor=doc,
        preferred=preferred,
        others=others,
        my_appts=my_appts,
        records=records,
        view=view
    )



@doctor_bp.route("/accept", methods=["POST"])
def accept():
    if "doctor" not in session:
        return redirect(url_for("doctor.login"))

    doc = session["doctor"]
    data = request.form

    conn = get_db()
    c = conn.cursor()

    # insert into assigned
    c.execute("""
        INSERT INTO assigned (patientId, dept, date, doctorId, timeSlot)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.get("patientId"),
        data.get("dept"),
        data.get("date"),
        doc["doctorId"],
        data.get("timeSlot")
    ))

    c.execute("""
        DELETE FROM waitingList 
        WHERE patientId=? AND date=?
    """, (
        data.get("patientId"),
        data.get("date")
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("doctor.dashboard"))



@doctor_bp.route("/decline", methods=["POST"])
def decline():
    if "doctor" not in session:
        return redirect(url_for("doctor.login"))

    data = request.form

    conn = get_db()
    c = conn.cursor()


    c.execute("""
        UPDATE waitingList 
        SET status=1 
        WHERE patientId=? AND date=?
    """, (
        data.get("patientId"),
        data.get("date")
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("doctor.dashboard"))


@doctor_bp.route("/submit_report", methods=["POST"])
def submit_report():
    if "doctor" not in session:
        return redirect(url_for("doctor.login"))

    doc = session["doctor"]
    data = request.form
    patient_id = data.get("patientId")

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM patient WHERE patientId=?", (patient_id,))
    patient = c.fetchone()
    if not patient:
        conn.close()
        return render_template("dashboarddoc.html", 
            error="Patient ID does not exist",
            doctor=doc,
            view="write"
        )

    c.execute("""
        SELECT * FROM assigned 
        WHERE patientId=? AND doctorId=?
    """, (patient_id, doc["doctorId"]))
    assignment = c.fetchone()
    if not assignment:
        conn.close()
        return render_template("dashboarddoc.html",
            error="You do not have an active appointment with this patient",
            doctor=doc,
            view="write"
        )

    # Insert consultation record
    c.execute("""
        INSERT INTO consultation 
        (patientId, date, doctorId, doctorName, prescription, result)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        patient_id,
        str(date.today()),
        doc["doctorId"],
        doc["doctorName"],
        data.get("prescription"),
        data.get("result")
    ))

    #Delete assignment after report submission
    c.execute("""
        DELETE FROM assigned 
        WHERE patientId=? AND doctorId=?
    """, (
        patient_id,
        doc["doctorId"]
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("doctor.dashboard"))

@doctor_bp.route("/account")
def doctor_account():
    if "doctor" not in session:
        return redirect(url_for("doctor.login"))

    doctor = session["doctor"]
    return render_template("doctorAccount.html", doctor=doctor)