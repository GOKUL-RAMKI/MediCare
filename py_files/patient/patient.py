from flask import Blueprint, render_template, request, redirect, url_for, session , send_file
import io
import os
import sqlite3
import datetime

patient_bp = Blueprint(
    "patient",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/patient/static"
)

def get_unit(drug_type):
    if not drug_type:
        return "pieces"

    dt = drug_type.strip().lower()
    if dt == "tablet":
        return "tablets"
    elif dt == "tonic":
        return "bottles"
    elif dt == "ointment":
        return "tubes"
    else:
        return "pieces"

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORDERS_FILE = os.path.join(BASE_DIR, "..", "..", "txt_files", "orders.txt")

def place_pharmacy_order(patient_id, drug_id, drug_name, drug_type, quantity):
    print("Writing to:", ORDERS_FILE)
    print("Exists:", os.path.exists(ORDERS_FILE))
    
    with open(ORDERS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{patient_id}|{drug_id}|{drug_name}|{drug_type}|{quantity}\n")
        f.flush()

    print("Written successfully")

def get_connection():
    conn = sqlite3.connect("hospital.db")
    conn.row_factory = sqlite3.Row
    return conn


def normalize_patient(row):
    if not row:
        return None

    return {
        "patientId": row["patientId"],
        "name": row["name"],
        "DOB": row["DOB"],
        "gender": row["gender"],
        "phoneNo": row["phoneNo"],
        "address": row["address"],
        "allergies": row["allergies"],
        "password": row["password"]
    }


def get_logged_in_patient():
    patient_id = session.get("patient_id")
    if not patient_id:
        return None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patient WHERE patientId = ?", (patient_id,))
    row = cur.fetchone()
    conn.close()

    return normalize_patient(row)


def get_candidate_patients():
    ids = session.get("login_candidates", [])
    if not ids:
        return []

    conn = get_connection()
    cur = conn.cursor()

    placeholders = ",".join("?" * len(ids))
    cur.execute(f"SELECT patientId, name FROM patient WHERE patientId IN ({placeholders})", ids)
    rows = cur.fetchall()
    conn.close()

    return [{"patientId": row["patientId"], "name": row["name"]} for row in rows]


@patient_bp.route("/")
def patient_menu():
    return render_template("patientMenu.html")


@patient_bp.route("/signup", methods=["GET", "POST"])
def patient_signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        dob = request.form.get("DOB", "").strip()
        gender = request.form.get("gender", "").strip()
        phone_no = request.form.get("phoneNo", "").strip()
        address = request.form.get("address", "").strip()
        allergies = request.form.get("allergies", "").strip()
        password = request.form.get("password", "").strip()

        if not all([name, dob, gender, phone_no, address, allergies, password]):
            return render_template("signupPatient.html", error="All fields are required.")

        try:
            datetime.date.fromisoformat(dob)
        except ValueError:
            return render_template("signupPatient.html", error="DOB must be in YYYY-MM-DD format.")

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM patient WHERE phoneNo = ? AND password = ?", (phone_no, password))
        existing_same_credentials = cur.fetchall()

        cur.execute("SELECT patientId FROM patient")
        rows = cur.fetchall()

        if not rows:
            new_id = "P1"
        else:
            max_num = 0
            for row in rows:
                pid = row["patientId"]
                if pid and pid.startswith("P") and pid[1:].isdigit():
                    max_num = max(max_num, int(pid[1:]))
            new_id = "P" + str(max_num + 1)

        cur.execute("""
            INSERT INTO patient (patientId, name, phoneNo, password, address, gender, allergies, DOB)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (new_id, name, phone_no, password, address, gender, allergies, dob))

        conn.commit()
        conn.close()

        return render_template("signupSuccess.html", patient_id=new_id)

    return render_template("signupPatient.html")


@patient_bp.route("/login", methods=["GET", "POST"])
def patient_login():
    if request.method == "POST":
        phone_no = request.form.get("phoneNo", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM patient WHERE phoneNo = ? AND password = ?",
            (phone_no, password)
        )
        rows = cur.fetchall()
        conn.close()

        if not rows:
            return render_template("loginPatient.html", error="Invalid phone number or password.")

        if len(rows) == 1:
            session["patient_id"] = rows[0]["patientId"]
            session.pop("login_candidates", None)
            return redirect(url_for("patient.patient_dashboard"))

        patients = []
        for row in rows:
            patients.append({
                "patientId": row["patientId"],
                "name": row["name"]
            })

        session["login_candidates"] = [p["patientId"] for p in patients]
        return render_template("selectPatient.html", patients=patients)

    return render_template("loginPatient.html")


@patient_bp.route("/select-profile", methods=["POST"])
def select_profile():
    patient_id = request.form.get("patientId", "").strip()
    allowed_ids = session.get("login_candidates", [])

    if not patient_id:
        patients = get_candidate_patients()
        return render_template("selectPatient.html", patients=patients, error="Enter a patient ID.")

    if patient_id not in allowed_ids:
        patients = get_candidate_patients()
        return render_template("selectPatient.html", patients=patients, error="Invalid patient selection.")

    session["patient_id"] = patient_id
    session.pop("login_candidates", None)
    return redirect(url_for("patient.patient_dashboard"))


@patient_bp.route("/dashboard")
def patient_dashboard():
    patient = get_logged_in_patient()
    if not patient:
        return redirect(url_for("patient.patient_login"))

    return render_template("dashboardPatient.html", patient=patient)


@patient_bp.route("/book-appointment", methods=["GET", "POST"])
def patient_book():
    patient = get_logged_in_patient()
    if not patient:
        return redirect(url_for("patient.patient_login"))

    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT doctorId, doctorName, dept FROM doctor ORDER BY dept, doctorName")
        doctors = [dict(row) for row in cur.fetchall()]

        success = None
        error = None

        if request.method == "POST":
            dept = request.form.get("dept", "").strip()
            preferred_doctor = request.form.get("preferredDoctor", "").strip()
            summary = request.form.get("summary", "").strip()
            date_str = request.form.get("date", "").strip()

            if not dept or not summary or not date_str:
                return render_template(
                    "bookAppointment.html",
                    patient=patient,
                    doctors=doctors,
                    error="Department, date, and summary are required.",
                    success=None
                )

            try:
                appt_date = datetime.date.fromisoformat(date_str)
                if appt_date < datetime.date.today():
                    return render_template(
                        "bookAppointment.html",
                        patient=patient,
                        doctors=doctors,
                        error="Invalid date.",
                        success=None
                    )
            except ValueError:
                return render_template(
                    "bookAppointment.html",
                    patient=patient,
                    doctors=doctors,
                    error="Invalid date format.",
                    success=None
                )

            cur.execute("""
                SELECT 1 FROM assigned 
                WHERE patientId=? AND date=?
            """, (patient["patientId"], date_str))
            assigned_exists = cur.fetchone()

            cur.execute("""
                SELECT 1 FROM waitingList 
                WHERE patientId=? AND date=?
            """, (patient["patientId"], date_str))
            waiting_exists = cur.fetchone()

            if assigned_exists or waiting_exists:
                return render_template(
                    "bookAppointment.html",
                    patient=patient,
                    doctors=doctors,
                    error="You already have an appointment or pending request on this date.",
                    success=None
                )

            # doctor validation
            preferred_doctor_value = None
            status_code = 2

            if preferred_doctor:
                cur.execute(
                    "SELECT * FROM doctor WHERE doctorId=? AND dept=?",
                    (preferred_doctor, dept)
                )
                doc = cur.fetchone()

                if not doc:
                    return render_template(
                        "bookAppointment.html",
                        patient=patient,
                        doctors=doctors,
                        error="Invalid preferred doctor.",
                        success=None
                    )

                preferred_doctor_value = preferred_doctor
                status_code = 0

            #  INSERT
            cur.execute("""
                INSERT INTO waitingList 
                (patientId, dept, date, preferredDoctor, summary, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                patient["patientId"],
                dept,
                date_str,
                preferred_doctor_value,
                summary,
                status_code
            ))

            conn.commit()

            success = "Appointment booked successfully."

        return render_template(
            "bookAppointment.html",
            patient=patient,
            doctors=doctors,
            error=error,
            success=success
        )

    finally:
        conn.close()
@patient_bp.route("/appointment-status", methods=["GET", "POST"])
def appointment_status():
    patient = get_logged_in_patient()
    if not patient:
        return redirect(url_for("patient.patient_login"))

    status_data = None
    error = None

    if request.method == "POST":
        date_str = request.form.get("date", "").strip()

        try:
            selected_date = datetime.date.fromisoformat(date_str)
            if selected_date < datetime.date.today():
                return render_template(
                    "appointmentStatus.html",
                    patient=patient,
                    status_data=None,
                    error="Invalid date. Please choose today or a future date."
                )
        except ValueError:
            return render_template(
                "appointmentStatus.html",
                patient=patient,
                status_data=None,
                error="Invalid date."
            )

        conn = get_connection()
        cur = conn.cursor()

        # Check assigned first (accepted appointments)
        cur.execute("""
            SELECT a.patientId, a.dept, a.date, a.doctorId, a.timeSlot, d.doctorName
            FROM assigned a
            LEFT JOIN doctor d ON a.doctorId = d.doctorId
            WHERE a.patientId = ? AND a.date = ?
        """, (patient["patientId"], str(selected_date)))
        assigned = cur.fetchone()

        if assigned:
            status_data = {
                "status": "Accepted",
                "date": assigned["date"],
                "dept": assigned["dept"],
                "doctorId": assigned["doctorId"],
                "doctorName": assigned["doctorName"],
                "timeSlot": assigned["timeSlot"]
            }
        else:
            # Check waitingList (pending requests)
            cur.execute("""
                SELECT w.patientId, w.dept, w.date, w.preferredDoctor, w.summary, w.status, d.doctorName
                FROM waitingList w
                LEFT JOIN doctor d ON w.preferredDoctor = d.doctorId
                WHERE w.patientId = ? AND w.date = ?
            """, (patient["patientId"], str(selected_date)))
            waiting = cur.fetchone()

            if waiting:
                # Map status: 0 or 2 = Pending, 1 = Declined (though should be in assigned)
                status_map = {0: "Pending", 2: "Pending", 1: "Declined"}
                status_data = {
                    "status": status_map.get(waiting["status"], "Unknown"),
                    "date": waiting["date"],
                    "dept": waiting["dept"],
                    "preferredDoctor": waiting["preferredDoctor"],
                    "preferredDoctorName": waiting["doctorName"],
                    "summary": waiting["summary"]
                }
            else:
                status_data = {
                    "status": "Not Found",
                    "date": str(selected_date)
                }

        conn.close()

    return render_template(
        "appointmentStatus.html",
        patient=patient,
        status_data=status_data,
        error=error
    )


@patient_bp.route("/consultation-history")
def consultation_history():
    patient = get_logged_in_patient()
    if not patient:
        return redirect(url_for("patient.patient_login"))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT date, doctorName, prescription, result
        FROM consultation
        WHERE patientId = ?
        ORDER BY date DESC
    """, (patient["patientId"],))

    consultations = []
    for row in cur.fetchall():
        consultations.append({
            "date": row["date"],
            "doctorName": row["doctorName"],
            "prescription": row["prescription"],
            "result": row["result"]
        })

    conn.close()
    return render_template("consultationHistory.html", patient=patient, consultations=consultations)


@patient_bp.route("/lab-reports")
def lab_reports():
    patient = get_logged_in_patient()
    if not patient:
        return redirect(url_for("patient.patient_login"))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT labId, testName, result, date
        FROM lab
        WHERE patientId = ?
        ORDER BY date DESC
    """, (patient["patientId"],))

    reports = []
    for row in cur.fetchall():
        reports.append({
            "labId": row["labId"],
            "testName": row["testName"],
            "result": row["result"],
            "date": row["date"]
        })

    conn.close()
    return render_template("labReports.html", patient=patient, reports=reports)

from flask import Response

@patient_bp.route("/download-lab-report/<lab_id>")
def download_lab_report(lab_id):
    patient = get_logged_in_patient()
    if not patient:
        return redirect(url_for("patient.patient_login"))

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT reportBlob, testName, date
        FROM lab
        WHERE labId = ? AND patientId = ?
    """, (lab_id, patient["patientId"]))

    report = cur.fetchone()
    conn.close()

    if not report or not report["reportBlob"]:
        return "Report not found", 404

    blob = report["reportBlob"]

    filename = f"{report['testName']}_{report['date']}.pdf"

    return Response(
        blob,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
    
@patient_bp.route("/pharmacy", methods=["GET", "POST"])
def pharmacy_search():
    patient = get_logged_in_patient()
    if not patient:
        return redirect(url_for("patient.patient_login"))

    conn = get_connection()
    cur = conn.cursor()

    drugs = []
    error = None
    success = None
    keyword = ""

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "search":
            keyword = request.form.get("keyword", "").strip()

            if not keyword:
                error = "Please enter a drug name or drug ID."
            else:
                cur.execute("""
                    SELECT drugId, drugName, quantity, price, expiryDate, drugType
                    FROM pharmacyInventory
                    WHERE LOWER(drugName) LIKE LOWER(?) OR LOWER(drugId) LIKE LOWER(?)
                """, (f"%{keyword}%", f"%{keyword}%"))

                rows = cur.fetchall()

                for row in rows:
                    drugs.append({
                        "drugId": row["drugId"],
                        "drugName": row["drugName"],
                        "quantity": row["quantity"],
                        "price": row["price"],
                        "expiryDate": row["expiryDate"],
                        "drugType": row["drugType"],
                        "unit": get_unit(row["drugType"])
                    })

                if not drugs:
                    error = f"No drugs found matching '{keyword}'."

        elif action == "order":
            keyword = request.form.get("keyword", "").strip()
            drug_id = request.form.get("drugId", "").strip()
            qty_input = request.form.get("quantity", "").strip()
            preview = request.form.get("preview", "no")

            if not qty_input.isdigit() or int(qty_input) <= 0:
                error = "Quantity must be a positive number."
            else:
                qty = int(qty_input)

                cur.execute("""
                    SELECT drugId, drugName, quantity, price, expiryDate, drugType
                    FROM pharmacyInventory
                    WHERE drugId = ?
                """, (drug_id,))
                selected = cur.fetchone()

                if not selected:
                    error = "Selected drug not found."

                elif qty > selected["quantity"]:
                    error = f"Only {selected['quantity']} {get_unit(selected['drugType'])} available."

                else:
                    total_price = qty * selected["price"]

                    #  STEP 1: PREVIEW MODE
                    if preview == "yes":
                        drugs = [{
                            "drugId": selected["drugId"],
                            "drugName": selected["drugName"],
                            "quantity": selected["quantity"],
                            "price": selected["price"],
                            "expiryDate": selected["expiryDate"],
                            "drugType": selected["drugType"],
                            "unit": get_unit(selected["drugType"])
                        }]

                        return render_template(
                            "pharmacySearch.html",
                            patient=patient,
                            drugs=drugs,
                            keyword=keyword,
                            total_price=total_price,
                            confirm_data={
                                "drugId": drug_id,
                                "quantity": qty
                            }
                        )

                    #  STEP 2: FINAL ORDER
                    place_pharmacy_order(
                        patient["patientId"],
                        selected["drugId"],
                        selected["drugName"],
                        selected["drugType"],
                        qty
                    )

                    success = f"Order placed for {selected['drugName']} x{qty} (₹{total_price})."

    conn.close()
    return render_template(
        "pharmacySearch.html",
        patient=patient,
        drugs=drugs,
        keyword=keyword,
        error=error,
        success=success
    )

@patient_bp.route("/account")
def patient_account():
    patient = get_logged_in_patient()
    if not patient:
        return redirect(url_for("patient.patient_login"))

    return render_template("patientAccount.html", patient=patient)

@patient_bp.route("/logout")
def patient_logout():
    session.pop("patient_id", None)
    session.pop("login_candidates", None)
    return redirect(url_for("patient.patient_menu"))