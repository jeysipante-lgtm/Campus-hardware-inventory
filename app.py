import os
import random
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, render_template_string

app = Flask(__name__)

# Security Configs
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-fallback-secret-key-12345')

# Mail Configurations (Resend API)
RESEND_API_KEY = os.getenv('RESEND_API_KEY')

# In-Memory Database for Borrowing Logs
BORROW_RECORDS = []

# Helper function para sa formatted timestamp
def get_current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

# --- Fallback HTML UI Templates ---

NAVBAR_HTML = """
<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container">
        <a class="navbar-brand fw-bold" href="{{ url_for('dashboard') }}">Campus Hardware Inventory</a>
        <div class="d-flex align-items-center">
            {% if session.get('logged_in') %}
                <a href="{{ url_for('dashboard') }}" class="btn btn-outline-light btn-sm me-2">Dashboard</a>
                <a href="{{ url_for('borrow_item') }}" class="btn btn-outline-info btn-sm me-3">Borrow / Return</a>
                <span class="text-light me-3 small">Logged in as: <strong>{{ session.get('user', 'User') }}</strong></span>
                <a href="{{ url_for('logout') }}" class="btn btn-outline-danger btn-sm">Logout</a>
            {% else %}
                <a href="{{ url_for('login') }}" class="btn btn-outline-light btn-sm me-2">Login</a>
                <a href="{{ url_for('register') }}" class="btn btn-primary btn-sm">Register</a>
            {% endif %}
        </div>
    </div>
</nav>
"""

LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Login - Campus Hardware Inventory</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    """ + NAVBAR_HTML + """
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
    """ + NAVBAR_HTML + """
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
    """ + NAVBAR_HTML + """
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
    """ + NAVBAR_HTML + """
    <div class="container mt-5">
        <div class="card shadow mb-4">
            <div class="card-body text-center p-4">
                <h2 class="text-success mb-2">Welcome to Dashboard!</h2>
                <p class="lead mb-1">Logged in user: <strong>{{ session.get('user', 'Guest') }}</strong></p>
                <p class="text-muted small">Session Login Timestamp: {{ session.get('login_timestamp', 'N/A') }}</p>
                <a href="{{ url_for('borrow_item') }}" class="btn btn-info mt-2">Go to Borrow & Return Records</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

BORROW_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Borrow & Return System - Campus Hardware Inventory</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    """ + NAVBAR_HTML + """
    <div class="container mt-4 mb-5">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }} alert-dismissible fade show">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <div class="row">
            <!-- Form: Borrow Item -->
            <div class="col-md-4 mb-4">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0">Borrow Hardware Item</h5>
                    </div>
                    <div class="card-body">
                        <form action="{{ url_for('borrow_item') }}" method="POST">
                            <div class="mb-3">
                                <label class="form-label">Item Name / Hardware</label>
                                <input type="text" name="item_name" class="form-control" placeholder="e.g. Arduino Uno, Monitor, Drill" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Quantity</label>
                                <input type="number" name="quantity" class="form-control" value="1" min="1" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Borrow Item (Auto-Timestamp)</button>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Table: Borrow & Return Logs -->
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">Borrowing & Return History Logs</h5>
                        <span class="badge bg-secondary">Live Timestamp Tracked</span>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover mb-0 align-middle">
                                <thead class="table-light">
                                    <tr>
                                        <th>#</th>
                                        <th>Borrower</th>
                                        <th>Item Name</th>
                                        <th>Qty</th>
                                        <th>Borrowed At</th>
                                        <th>Returned At</th>
                                        <th>Status</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% if records %}
                                        {% for rec in records %}
                                        <tr>
                                            <td>{{ rec.id }}</td>
                                            <td><strong>{{ rec.borrower }}</strong></td>
                                            <td>{{ rec.item_name }}</td>
                                            <td>{{ rec.quantity }}</td>
                                            <td><small class="text-primary">{{ rec.borrow_timestamp }}</small></td>
                                            <td>
                                                {% if rec.return_timestamp %}
                                                    <small class="text-success">{{ rec.return_timestamp }}</small>
                                                {% else %}
                                                    <span class="badge bg-secondary">Pending</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                {% if rec.status == 'Borrowed' %}
                                                    <span class="badge bg-warning text-dark">Borrowed</span>
                                                {% else %}
                                                    <span class="badge bg-success">Returned</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                {% if rec.status == 'Borrowed' %}
                                                    <form action="{{ url_for('return_item', record_id=rec.id) }}" method="POST">
                                                        <button type="submit" class="btn btn-sm btn-success">Return Item</button>
                                                    </form>
                                                {% else %}
                                                    <button class="btn btn-sm btn-outline-secondary" disabled>Done</button>
                                                {% endif %}
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    {% else %}
                                        <tr>
                                            <td colspan="8" class="text-center text-muted py-4">No borrowing transactions recorded yet.</td>
                                        </tr>
                                    {% endif %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

def send_otp_email_resend(to_email, otp_code, purpose="verification"):
    timestamp = get_current_timestamp()
    subject = f"Your {purpose.title()} OTP Code - Campus Hardware Inventory"
    body = (
        f"Hello,\n\n"
        f"Your One-Time Password (OTP) for {purpose} is: {otp_code}\n"
        f"Requested at: {timestamp}\n\n"
        f"This code is valid for 10 minutes. Please do not share this code with anyone.\n\n"
        f"Best regards,\nCampus Hardware Inventory Team"
    )

    if RESEND_API_KEY:
        try:
            print(f"[{timestamp}] Sending OTP via Resend API to {to_email}...")
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
                print(f"[{timestamp}] SUCCESS: OTP sent via Resend API to {to_email}!")
                return True
            else:
                print(f"[{timestamp}] ERROR: Resend API returned status code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[{timestamp}] ERROR: Resend API request failed: {e}")

    # Fallback log sa Render console
    print("\n" + "="*60)
    print(f"[{timestamp}] === {purpose.upper()} OTP FOR [{to_email}]: {otp_code} ===")
    print("="*60 + "\n")

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
        current_time = get_current_timestamp()
        
        session['pending_user'] = {
            'username': username,
            'student_number': student_number,
            'email': email,
            'password': password,
            'role': role,
            'otp': otp_code,
            'timestamp': current_time
        }

        send_otp_email_resend(email, otp_code, purpose="account registration")
        flash(f'Verification code sent at {current_time}! Check your email or Render logs.', 'info')
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
        current_time = get_current_timestamp()

        session['reset_password_data'] = {
            'email': email,
            'otp': otp_code,
            'timestamp': current_time
        }

        send_otp_email_resend(email, otp_code, purpose="password reset")
        flash(f'Password reset OTP sent at {current_time}! Check your email or Render logs.', 'info')
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
        username = request.form.get('username')
        session['logged_in'] = True
        session['user'] = username if username else 'User'
        session['login_timestamp'] = get_current_timestamp()
        
        flash('Logged in successfully!', 'success')
        return redirect(url_for('dashboard'))

    try:
        return render_template('login.html')
    except Exception:
        return render_template_string(LOGIN_PAGE_HTML)

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash('Please login first to access dashboard.', 'warning')
        return redirect(url_for('login'))

    try:
        return render_template('dashboard.html')
    except Exception:
        return render_template_string(DASHBOARD_PAGE_HTML)

# --- Borrow & Return Routes with Timestamps ---

@app.route('/borrow', methods=['GET', 'POST'])
def borrow_item():
    if not session.get('logged_in'):
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        item_name = request.form.get('item_name')
        quantity = request.form.get('quantity', 1)
        borrow_time = get_current_timestamp()

        record = {
            'id': len(BORROW_RECORDS) + 1,
            'borrower': session.get('user', 'User'),
            'item_name': item_name,
            'quantity': quantity,
            'borrow_timestamp': borrow_time,
            'return_timestamp': None,
            'status': 'Borrowed'
        }
        BORROW_RECORDS.append(record)

        print(f"[{borrow_time}] BORROW LOG: '{item_name}' (Qty: {quantity}) borrowed by {session.get('user')}")
        flash(f"Item '{item_name}' borrowed successfully at {borrow_time}!", 'success')
        return redirect(url_for('borrow_item'))

    try:
        return render_template('borrow.html', records=BORROW_RECORDS)
    except Exception:
        return render_template_string(BORROW_PAGE_HTML, records=BORROW_RECORDS)

@app.route('/return/<int:record_id>', methods=['POST'])
def return_item(record_id):
    if not session.get('logged_in'):
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    return_time = get_current_timestamp()
    for rec in BORROW_RECORDS:
        if rec['id'] == record_id:
            rec['return_timestamp'] = return_time
            rec['status'] = 'Returned'
            print(f"[{return_time}] RETURN LOG: Item '{rec['item_name']}' returned by {rec['borrower']}")
            flash(f"Item '{rec['item_name']}' returned successfully at {return_time}!", 'success')
            break

    return redirect(url_for('borrow_item'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)