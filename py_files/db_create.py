import sqlite3

conn = sqlite3.connect("hospital.db")
cursor = conn.cursor()
def create():
    cursor.execute('''CREATE TABLE IF NOT EXISTS patient(
                patientId TEXT PRIMARY KEY,
                name TEXT,
                phoneNo TEXT,
                password TEXT,
                address TEXT,
                gender TEXT,
                allergies TEXT,
                DOB TEXT
                )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS consultation(
                patientId TEXT,
                date TEXT,
                doctorId TEXT,
                doctorName TEXT,
                prescription TEXT,
                result TEXT,
                FOREIGN KEY (patientId) REFERENCES patient(patientId)
                )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS pharmacyInventory(
               drugId TEXT,
               batchId TEXT,
               drugName TEXT,
               quantity INTEGER,
               price REAL,
               expiryDate TEXT,
               drugType TEXT
               )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS lab(
                labId TEXT,
                patientId TEXT,
                testName TEXT,
                doctorId TEXT,
                reportBlob BLOB,
                result TEXT,
                date TEXT
                )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS doctor(
                doctorId TEXT PRIMARY KEY,
                doctorName TEXT,
                age INTEGER,
                gender TEXT,
                dept TEXT,
                speciality TEXT,
                password TEXT
                )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS waitingList(
                patientId TEXT,
                dept TEXT,
                date TEXT,
                preferredDoctor TEXT,
                summary TEXT,
                status INTEGER
                )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS assigned(
                patientId TEXT,
                dept TEXT,
                date TEXT,
                doctorId TEXT,
                timeSlot TEXT
                )''')
    
    conn.commit()
create()