from flask import Blueprint, render_template, request, redirect, url_for, session
import sqlite3
import os

pharmacy_bp = Blueprint(
    'pharmacy',
    __name__,
    template_folder='templates',
    static_folder='static'
)

PHARMACY_PASSWORD = "pharmacy123"

# ---------------- PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# py_files/pharmacy / py_files / root / txt_files
ORDERS_FILE = os.path.abspath(
    os.path.join(BASE_DIR, "..", "..", "txt_files", "orders.txt")
)

DB_PATH = os.path.join(BASE_DIR, "..", "hospital.db")


# ---------------- DB ----------------

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- HOME ----------------

@pharmacy_bp.route("/")
def home():
    return redirect(url_for("pharmacy.login"))


# ---------------- LOGIN ----------------

@pharmacy_bp.route("/login", methods=["GET", "POST"])
def login():
    if "pharmacy" in session:
        return redirect(url_for("pharmacy.dashboard"))

    if request.method == "POST":
        password = request.form.get("password", "").strip()

        if password != PHARMACY_PASSWORD:
            return render_template("pharmacy_login.html", error="Invalid password")

        session["pharmacy"] = True
        return redirect(url_for("pharmacy.dashboard"))

    return render_template("pharmacy_login.html")


# ---------------- DASHBOARD ----------------

@pharmacy_bp.route("/dashboard")
def dashboard():
    if "pharmacy" not in session:
        return redirect(url_for("pharmacy.login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pharmacyInventory")
    drugs = cursor.fetchall()

    conn.close()

    return render_template("pharmacy_dashboard.html", drugs=drugs)


# ---------------- ADD STOCK ----------------

@pharmacy_bp.route("/add", methods=["POST"])
def add_stock():
    if "pharmacy" not in session:
        return redirect(url_for("pharmacy.login"))

    data = request.form

    drug_id = data.get("drugId")
    batch_id = data.get("batchId")
    drug_name = data.get("drugName")
    quantity = data.get("quantity")
    price = data.get("price")
    expiry = data.get("expiryDate")
    drug_type = data.get("drugType")

    if not quantity.isdigit():
        return "Quantity must be a number"

    try:
        price = float(price)
    except:
        return "Price must be a number"

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO pharmacyInventory
            (drugId, batchId, drugName, quantity, price, expiryDate, drugType)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (drug_id, batch_id, drug_name, int(quantity), price, expiry, drug_type))

        conn.commit()

    except sqlite3.Error as e:
        return f"Database Error: {e}"

    finally:
        conn.close()

    return redirect(url_for("pharmacy.dashboard"))


# ---------------- VIEW ORDERS ----------------

@pharmacy_bp.route("/orders")
def orders():
    if "pharmacy" not in session:
        return redirect(url_for("pharmacy.login"))

    orders = []

    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

            for line in lines:
                try:
                    p, d_id, d_name, d_type, qty = line.split("|")
                    orders.append({
                        "patient": p,
                        "drugId": d_id,
                        "drugName": d_name,
                        "drugType": d_type,
                        "quantity": int(qty)
                    })
                except:
                    print("Invalid line:", line)

    return render_template("pharmacy_orders.html", orders=orders)

# ---------------- ACCEPT ORDER ----------------

@pharmacy_bp.route("/accept_order/<int:index>")
def accept_order(index):
    if "pharmacy" not in session:
        return redirect(url_for("pharmacy.login"))

    if not os.path.exists(ORDERS_FILE):
        return redirect(url_for("pharmacy.orders"))

    with open(ORDERS_FILE, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if not (0 <= index < len(lines)):
        return redirect(url_for("pharmacy.orders"))

    target_line = lines[index]

    #  unpack with drug_type
    p, drug_id, drug_name, drug_type, qty = target_line.split("|")
    qty = int(qty)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT quantity FROM pharmacyInventory 
            WHERE drugId=? AND drugName=? AND drugType=?
        """, (drug_id, drug_name, drug_type))

        result = cursor.fetchone()

        if result:
            current_qty = result["quantity"]

            if current_qty >= qty:
                cursor.execute("""
                    UPDATE pharmacyInventory
                    SET quantity = quantity - ?
                    WHERE drugId=? AND drugName=? AND drugType=?
                """, (qty, drug_id, drug_name, drug_type))
            else:
                print("Not enough stock")
        else:
            print("Drug not found in inventory")

        conn.commit()

    except Exception as e:
        print("ERROR:", e)

    finally:
        conn.close()

    lines.pop(index)

    with open(ORDERS_FILE, "w") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))

    return redirect(url_for("pharmacy.orders"))

# ---------------- DECLINE ORDER ----------------

@pharmacy_bp.route("/decline_order/<int:index>")
def decline_order(index):
    if "pharmacy" not in session:
        return redirect(url_for("pharmacy.login"))

    if not os.path.exists(ORDERS_FILE):
        return redirect(url_for("pharmacy.orders"))

    with open(ORDERS_FILE, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if not (0 <= index < len(lines)):
        return redirect(url_for("pharmacy.orders"))

    target_line = lines[index]

    # SAFE REMOVE
    lines = [line for line in lines if line != target_line]

    with open(ORDERS_FILE, "w") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))

    return redirect(url_for("pharmacy.orders"))


# ---------------- LOGOUT ----------------

@pharmacy_bp.route("/logout")
def logout():
    session.pop("pharmacy", None)
    return redirect(url_for("pharmacy.login"))