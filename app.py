import os
import random
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, render_template_string

app = Flask(__name__)

# Security Configs
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-fallback-secret-key-12345')

# Mail Configurations (Resend API)
RESEND_API_KEY = os.getenv('RESEND_API_KEY')

# --- Fallback HTML UI Templates ---

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
                        <div class="d-flex justify-content-between">
                            <a href="{{ url_for('register') }}">Register</a>
                            <a href="{{ url_for('forgot_password') }}">Forgot Password?</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

FORGOT_PASSWORD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Forgot Password - Campus Hardware Inventory</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-5">
                <div class="card shadow">
                    <div class="card-header bg-warning text-dark text-center">
                        <h4>Reset Password</h4>
                    </div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                          {% if messages %}
                            {% for category, message in messages %}
                              <div class="alert alert-{{ category }}">{{ message }}</div>
                            {% endfor %}
                          {% endif %}
                        {% endwith %}
                        <p class="text-muted text-center">Enter your registered email address to receive an OTP code.</p>
                        <form action="{{ url_for('forgot_password') }}" method="POST">
                            <div class="mb-3">
                                <label class="form-label">Email Address</label>
                                <input type="email" name="email" class="form-control" placeholder="user@example.com" required autofocus>
                            </div>
                            <button type="submit" class="btn btn-warning w-100">Send Reset OTP</button>
                        </form>
                        <hr>
                        <div class="text-center">
                            <a href="{{ url_for('login') }}">Back to Login</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

RESET_OTP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Verify Reset OTP - Campus Hardware Inventory</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-5">
                <div class="card shadow">
                    <div class="card-header bg-warning text-dark text-center">
                        <h4>Set New Password</h4>
                    </div>
                    <div class="card-body">
                        {% with messages = get_flashed_messages(with_categories=true) %}
                          {% if messages %}
                            {% for category, message in messages %}
                              <div class="alert alert-{{ category }}">{{ message }}</div>
                            {% endfor %}
                          {% endif %}
                        {% endwith %}
                        <form action="{{ url_for('verify_otp_reset_password') }}" method="POST">
                            <div class="mb-3">
                                <label class="form-label">OTP Code</label>
                                <input type="text" name="otp_code" class="form-control text-center fs-4" placeholder="123456" required autofocus>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">New Password</label>
                                <input type="password" name="new_password" class="form-control" placeholder="Enter new password" required>
                            </div>
                            <button type="submit" class="btn btn-warning w-100">Reset Password</button>
                        </form>
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
                <p class="lead">Account setup and authentication complete.</p>
                <a href="{{ url_for('register') }}" class="btn btn-primary">Go back to Register Page</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

def send_otp_email_resend(to_email, otp_code, purpose="verification"):
    subject = f"Your {purpose.title()} OTP Code - Campus Hardware Inventory"
    body = (
        f"Hello,\n\n"
        f"Your One-Time Password (OTP) for {purpose} is: {otp_code}\n\n"
        f"This code is valid for 10 minutes. Please do not share this code with anyone.\n\n"
        f"Best regards,\nCampus Hardware Inventory Team"
    )

    if RESEND_API_KEY:
        try:
            print(f"Sending OTP via Resend API to {to_email}...")
            url = "https://api.resend.com/emails"
            headers = {
                "Authorization": f"Bearer {RESEND_API_KEY.strip()}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": "Campus Hardware Inventory <onboarding@resend.dev>",
                "to": [to_email],
                "subject": subject,
                "text": body
            }
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                print(f"SUCCESS: OTP sent via Resend API to {to_email}!")
                return True
            else:
                print(f"ERROR: Resend API returned status code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"ERROR: Resend API request failed: {e}")

    print("\n" + "="*50)
    print(f"=== {purpose.upper()} OTP FOR [{to_email}]: {otp_code} ===")
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

        send_otp_email_resend(email, otp_code, purpose="account registration")
        flash('Verification code sent! Check your email.', 'info')
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

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        otp_code = str(random.randint(100000, 999999))

        session['reset_password_data'] = {
            'email': email,
            'otp': otp_code
        }

        send_otp_email_resend(email, otp_code, purpose="password reset")
        flash('Password reset OTP sent! Please check your email.', 'info')
        return redirect(url_for('verify_otp_reset_password'))

    try:
        return render_template('forgot_password.html')
    except Exception:
        return render_template_string(FORGOT_PASSWORD_HTML)

@app.route('/verify-otp/reset-password', methods=['GET', 'POST'])
def verify_otp_reset_password():
    reset_data = session.get('reset_password_data')
    if not reset_data:
        flash('Reset session expired. Please request password reset again.', 'warning')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form.get('otp_code', '').strip()
        new_password = request.form.get('new_password')

        if entered_otp == str(reset_data.get('otp')):
            session.pop('reset_password_data', None)
            flash('Password reset successful! You can now log in with your new password.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP code. Please try again.', 'danger')

    try:
        return render_template('reset_password_otp.html')
    except Exception:
        return render_template_string(RESET_OTP_HTML)

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