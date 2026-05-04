from flask import Flask

app = Flask(__name__)
app.secret_key = "super_secret_key"

# import blueprints
from patient.patient import patient_bp
from doctor.doctor import doctor_bp
from lab.lab import lab_bp
from pharmacy.pharmacy import pharmacy_bp

# register with prefix 
app.register_blueprint(patient_bp, url_prefix="/patient")
app.register_blueprint(doctor_bp, url_prefix="/doctor")
app.register_blueprint(lab_bp, url_prefix="/lab")
app.register_blueprint(pharmacy_bp, url_prefix="/pharmacy")

# home route 
@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Hospital Management System</title>
        <style>
            body {
                margin: 0;
                font-family: sans-serif;
                background: linear-gradient(135deg, #0a192f, #1a3a5f);
                color: white;
            }
            .container {
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding: 20px;
                text-align: center;
                
            }
            .card {
                background: #0a192f;
                border-radius: 18px;
                box-shadow: 0 20px 50px rgba(15, 32, 56, 0.12);
                padding: 40px 32px;
                max-width: 520px;
                width: 100%;
            }
            h1 {
                margin: 0 0 12px;
                font-size: 2.4rem;
            }
            p {
                margin: 0 0 28px;
                color: #555;
                line-height: 1.6;
            }
            
            .footer {
                margin-top: 24px;
                font-size: 0.92rem;
                color: #777;
            }

            ul {
                list-style: none;
                padding: 0;
                margin: 0;
            }

            ul li {
                margin-bottom: 16px;
            }

            a {
                display: inline-block;
                background: #ffffff;
                color: #0a192f;
                text-decoration: none;
                padding: 14px 24px;
                border-radius: 12px;
                width: 200px;
                transition: transform 0.2s ease, box-shadow 0.2s ease;
                font-weight: 600;
            }

            a:hover {
                transform: translateY(-2px);
                box-shadow: 0 12px 24px rgba(255, 255, 255, 0.18);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1><b> Hospital Management System</b></h1><br><Br>
                
                <ul>
                    <li><a href="/patient">Patient Portal</a></li>
                    <li><a href="/doctor">Doctor Portal</a></li>
                    <li><a href="/lab">Lab Portal</a></li>
                    <li><a href="/pharmacy">Pharmacy Portal</a></li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(debug=True)