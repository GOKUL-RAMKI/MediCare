"""Load sample data into hospital.db.

This script inserts sample rows into:
- patient
- doctor
- pharmacyInventory

It is safe to run multiple times because it removes only the sample IDs first.

Usage:
    python load_hospital_sample_data.py
    python load_hospital_sample_data.py /path/to/hospital.db
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


PATIENT_ROWS = [
    ("P1", "Arun Kumar", "9876543210", "pass123", "12, North Street, Coimbatore", "Male", "None", "2001-06-14"),
    ("P2", "Kavya S", "9876543210", "pass123", "45, South Street, Coimbatore", "Female", "Peanut allergy", "2002-11-20"),
    ("P3", "Meera N", "9123456780", "meera789", "8, Lake View Road, Erode", "Female", "Dust allergy", "1999-02-03"),
]

DOCTOR_ROWS = [
    ("D6A6886", "Dr. Hamza", 42, "Male", "Cardiology", "Heart Specialist", "doc123"),
    ("D257C68", "Dr. Rahman Dakait", 39, "Female", "Cardiology", "Interventional Cardiologist", "doc124"),
    ("DFF5C73", "Dr. Usair Baloch", 35, "Female", "Orthopedics", "Bone & Joint Specialist", "doc125"),
    ("DC0743D", "Dr. Jameel Jaleel", 46, "Male", "Dermatology", "Skin Specialist", "doc126"),
    ("DB29B6B", "Dr. Yalina", 46, "Female", "Dermatology", "Skin Specialist", "doc126"),
]

PHARMACY_ROWS = [
    ("DRG1001", "B001", "Paracetamol", 120, 12.50, "2027-06-30", "tablet"),
    ("DRG1002", "B002", "Amoxicillin", 80, 28.00, "2026-12-31", "capsule"),
    ("DRG1003", "B003", "Cough Syrup", 55, 65.00, "2026-10-15", "tonic"),
    ("DRG1004", "B004", "Clotrimazole Cream", 40, 34.75, "2027-03-20", "cream"),
    ("DRG1005", "B005", "Metformin", 90, 18.25, "2027-01-31", "tablet"),
    ("DRG1006", "B006", "Eye Drops", 70, 22.00, "2026-08-12", "drops"),
    ("DRG1007", "B007", "Insulin Injection", 25, 180.00, "2026-09-30", "injection"),
    ("DRG1008", "B008", "ORS Powder", 150, 8.00, "2027-05-11", "powder"),
    ("DRG1009", "B009", "Diclofenac Gel", 60, 44.00, "2027-04-18", "gel"),
    ("DRG1010", "B010", "Vitamin D3", 110, 52.00, "2027-02-28", "tablet"),
]


def find_db_path(arg_path: str | None = None) -> Path:
    if arg_path:
        return Path(arg_path).expanduser().resolve()

    script_dir = Path(__file__).resolve().parent
    candidates = [
        script_dir / "hospital.db",
        script_dir / "py_files" / "hospital.db",
        Path.cwd() / "hospital.db",
        Path.cwd() / "py_files" / "hospital.db",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    # default to the most likely location next to the script
    return (script_dir / "hospital.db").resolve()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_samples(db_path: Path) -> None:
    ensure_parent(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()

        # Remove only our sample rows so the script can be run again safely.
        cur.executemany("DELETE FROM patient WHERE patientId = ?", [(row[0],) for row in PATIENT_ROWS])
        cur.executemany("DELETE FROM doctor WHERE doctorId = ?", [(row[0],) for row in DOCTOR_ROWS])
        cur.executemany("DELETE FROM pharmacyInventory WHERE drugId = ?", [(row[0],) for row in PHARMACY_ROWS])

        cur.executemany(
            """
            INSERT INTO patient (patientId, name, phoneNo, password, address, gender, allergies, DOB)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            PATIENT_ROWS,
        )

        cur.executemany(
            """
            INSERT INTO doctor (doctorId, doctorName, age, gender, dept, speciality, password)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            DOCTOR_ROWS,
        )

        cur.executemany(
            """
            INSERT INTO pharmacyInventory (drugId, batchId, drugName, quantity, price, expiryDate, drugType)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            PHARMACY_ROWS,
        )

        conn.commit()
    finally:
        conn.close()


def main() -> int:
    db_arg = sys.argv[1] if len(sys.argv) > 1 else None
    db_path = find_db_path(db_arg)

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return 1

    load_samples(db_path)
    print(f"Loaded sample data into: {db_path}")
    print(f"Patients inserted: {len(PATIENT_ROWS)}")
    print(f"Doctors inserted: {len(DOCTOR_ROWS)}")
    print(f"Pharmacy records inserted: {len(PHARMACY_ROWS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
