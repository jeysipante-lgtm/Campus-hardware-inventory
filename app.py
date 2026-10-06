import os
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, flash, session, render_template_string

app = Flask(__name__)

# Security Configs
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-fallback-secret-key-12345')

# Mail Configurations
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_LOGIN = os.getenv('SMTP_LOGIN')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SENDER_EMAIL = os.getenv('SENDER_EMAIL')

# Fallback HTML UI Templates
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Campus Hardware Inventory</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-5">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white text-center">
                        <h4>Login Account</h4>
                    </div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                          {% if messages %}
                            {% for category, message in messages %}
                              <div class="alert alert-{{ category }}">{{ message }}</div>
                            {% endfor %}
                          {% endif %}
                        {% endwith %}
                        <form action="{{ url_for('login') }}" method="POST">
                            <div class="mb-3">
                                <label class="form-label">Username or Email</label>
                                <input type="text" name="username" class="form-control" required autofocus>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Password</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Login</button>
                        </form>
                        <hr>
                        <div class="text-center">
                            <a href="{{ url_for('register') }}">Don't have an account? Register here</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Campus Hardware Inventory</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="#">Campus Hardware Inventory System</a>
            <a href="{{ url_for('login') }}" class="btn btn-outline-light btn-sm">Logout</a>
        </div>
    </nav>
    <div class="container mt-5">
        <div class="card shadow">
            <div class="card-body text-center p-5">
                <h1 class="text-success mb-3">Welcome to Dashboard!</h1>
                <p class="lead">Account verification and login setup successfully completed.</p>
                <a href="{{ url_for('register') }}" class="btn btn-primary">Go back to Register Page</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

def send_otp_email(to_email, otp_code):
    """Attempts SMTP email delivery with automatic fallback to Render Logs"""
    subject = "Your Verification Code - Campus Hardware Inventory"
    body = f"Your One-Time Password (OTP) for account verification is: {otp_code}\n\nThis code will expire shortly."

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL or 'noreply@campus.edu'
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if SMTP_LOGIN and SMTP_PASSWORD:
        try:
            print(f"Connecting via SSL port 465 to {SMTP_SERVER}...")
            with smtplib.SMTP_SSL(SMTP_SERVER, 465, timeout=5) as server:
                server.login(SMTP_LOGIN, SMTP_PASSWORD)
                server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
            print("Successfully sent OTP email via SSL 465")
        except Exception as e:
            print(f"SMTP delivery unavailable: {e}")

    print("\n" + "="*50)
    print(f"=== VERIFICATION OTP FOR [{to_email}]: {otp_code} ===")
    print("="*50 + "\n")

    return True

@app.route('/')
def index():
    return redirect(url_for('register'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        student_number = request.form.get('student_number', '')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'Student')

        otp_code = str(random.randint(100000, 999999))
        
        session['pending_user'] = {
            'username': username,
            'student_number': student_number,
            'email': email,
            'password': password,
            'role': role,
            'otp': otp_code
        }

        send_otp_email(email, otp_code)
        flash('Verification code generated! Check Render Logs for the OTP.', 'info')
        return redirect(url_for('verify_otp_register'))

    try:
        return render_template('register.html')
    except Exception:
        return redirect(url_for('login'))

@app.route('/verify-otp/register', methods=['GET', 'POST'])
def verify_otp_register():
    pending_user = session.get('pending_user')
    if not pending_user:
        flash('Session expired. Please register again.', 'warning')
        return redirect(url_for('register'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp_code', '').strip()
        if entered_otp == str(pending_user.get('otp')):
            session.pop('pending_user', None)
            flash('Registration successful! You can now login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP code. Please try again.', 'danger')

    try:
        return render_template('otp_verify.html', action_url=url_for('verify_otp_register'))
    except Exception:
        return render_template_string(LOGIN_PAGE_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        flash('Logged in successfully!', 'success')
        return redirect(url_for('dashboard'))

    try:
        return render_template('login.html')
    except Exception:
        return render_template_string(LOGIN_PAGE_HTML)

@app.route('/dashboard')
def dashboard():
    try:
        return render_template('dashboard.html')
    except Exception:
        return render_template_string(DASHBOARD_PAGE_HTML)

if __name__ == '__main__':
    app.run(debug=True)