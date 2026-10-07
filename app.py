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
<nav class="navbar navbar-expand-lg navbar-dark bg-dark shadow-sm">
    <div class="container">
        <a class="navbar-brand fw-bold" href="{{ url_for('dashboard') }}">Campus Hardware Inventory (Admin)</a>
        <div class="d-flex align-items-center">
            {% if session.get('logged_in') %}
                <span class="text-light me-3 small">Logged in as: <strong class="text-warning">{{ session.get('user', 'Admin') }}</strong></span>
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
                        <h4>Admin Login</h4>
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
                                <input type="text" name="username" class="form-control" placeholder="Admin username" required autofocus>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Password</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Login to Dashboard</button>
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
    <title>Admin Dashboard - Campus Hardware Inventory</title>
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

        <!-- Quick Summary Cards -->
        <div class="row mb-4">
            <div class="col-md-4">
                <div class="card bg-primary text-white shadow">
                    <div class="card-body text-center">
                        <h5>Total Borrowed</h5>
                        <h2>{{ records | length }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card bg-warning text-dark shadow">
                    <div class="card-body text-center">
                        <h5>Currently Out (Pending Return)</h5>
                        <h2>{{ records | selectattr('status', 'equalto', 'Borrowed') | list | length }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card bg-success text-white shadow">
                    <div class="card-body text-center">
                        <h5>Returned Items</h5>
                        <h2>{{ records | selectattr('status', 'equalto', 'Returned') | list | length }}</h2>
                    </div>
                </div>
            </div>
        </div>

        <div class="row">
            <!-- Form: Record New Borrow Out -->
            <div class="col-md-4 mb-4">
                <div class="card shadow">
                    <div class="card-header bg-dark text-white">
                        <h5 class="mb-0">Record Item Borrowed (Out)</h5>
                    </div>
                    <div class="card-body">
                        <form action="{{ url_for('borrow_item') }}" method="POST">
                            <div class="mb-3">
                                <label class="form-label">Borrower Name / Student</label>
                                <input type="text" name="borrower" class="form-control" placeholder="e.g. Juan Cruz" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Hardware Item</label>
                                <input type="text" name="item_name" class="form-control" placeholder="e.g. Arduino, Projector" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Quantity</label>
                                <input type="number" name="quantity" class="form-control" value="1" min="1" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Log Borrowed (Out)</button>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Table: Admin Borrowing & Return Management -->
            <div class="col-md-8">
                <div class="card shadow">
                    <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">Borrow, Out & Return Monitoring</h5>
                        <span class="badge bg-warning text-dark">Admin Live View</span>
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
                                        <th>Out Timestamp</th>
                                        <th>Return Timestamp</th>
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
                                            <td><small class="text-primary fw-bold">{{ rec.borrow_timestamp }}</small></td>
                                            <td>
                                                {% if rec.return_timestamp %}
                                                    <small class="text-success fw-bold">{{ rec.return_timestamp }}</small>
                                                {% else %}
                                                    <span class="badge bg-secondary">Out (Pending)</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                {% if rec.status == 'Borrowed' %}
                                                    <span class="badge bg-danger">OUT</span>
                                                {% else %}
                                                    <span class="badge bg-success">RETURNED</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                {% if rec.status == 'Borrowed' %}
                                                    <form action="{{ url_for('return_item', record_id=rec.id) }}" method="POST">
                                                        <button type="submit" class="btn btn-sm btn-success">Mark Returned</button>
                                                    </form>
                                                {% else %}
                                                    <button class="btn btn-sm btn-outline-secondary" disabled>Done</button>
                                                {% endif %}
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    {% else %}
                                        <tr>
                                            <td colspan="8" class="text-center text-muted py-4">No borrow or return records yet.</td>
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
        f"This code is valid for 10 minutes.\n\n"
        f"Best regards,\nCampus Hardware Inventory Team"
    )

    if RESEND_API_KEY:
        try:
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
            requests.post(url, json=payload, headers=headers, timeout=10)
        except Exception as e:
            print(f"ERROR: Resend API request failed: {e}")

    print(f"\n[{timestamp}] === {purpose.upper()} OTP FOR [{to_email}]: {otp_code} ===\n")
    return True

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        session['logged_in'] = True
        session['user'] = username if username else 'Admin'
        session['login_timestamp'] = get_current_timestamp()
        
        flash('Logged in successfully as Admin!', 'success')
        return redirect(url_for('dashboard'))

    try:
        return render_template('login.html')
    except Exception:
        return render_template_string(LOGIN_PAGE_HTML)

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash('Please login first to access admin dashboard.', 'warning')
        return redirect(url_for('login'))

    try:
        return render_template('dashboard.html', records=BORROW_RECORDS)
    except Exception:
        return render_template_string(DASHBOARD_PAGE_HTML, records=BORROW_RECORDS)

@app.route('/borrow', methods=['POST'])
def borrow_item():
    if not session.get('logged_in'):
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    borrower = request.form.get('borrower')
    item_name = request.form.get('item_name')
    quantity = request.form.get('quantity', 1)
    borrow_time = get_current_timestamp()

    record = {
        'id': len(BORROW_RECORDS) + 1,
        'borrower': borrower if borrower else session.get('user', 'Admin'),
        'item_name': item_name,
        'quantity': quantity,
        'borrow_timestamp': borrow_time,
        'return_timestamp': None,
        'status': 'Borrowed'
    }
    BORROW_RECORDS.append(record)

    flash(f"Item '{item_name}' marked as OUT at {borrow_time}!", 'success')
    return redirect(url_for('dashboard'))

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
            flash(f"Item '{rec['item_name']}' returned successfully at {return_time}!", 'success')
            break

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)