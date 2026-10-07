import os
from datetime import datetime
from flask import Flask, request, redirect, url_for, flash, session, render_template_string

app = Flask(__name__)

# Security Configs
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-fallback-secret-key-12345')

# In-Memory Database
HARDWARE_INVENTORY = [
    {'id': 1, 'name': 'Arduino Uno', 'category': 'Microcontroller', 'quantity': 10},
    {'id': 2, 'name': 'LCD Display 16x2', 'category': 'Display', 'quantity': 5}
]
BORROW_RECORDS = []

def get_current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

# --- HTML UI Templates ---

NAVBAR_HTML = """
<nav class="navbar navbar-expand-lg navbar-dark bg-dark shadow-sm">
    <div class="container">
        <a class="navbar-brand fw-bold" href="{{ url_for('dashboard') }}">Campus Hardware Inventory</a>
        <div class="d-flex align-items-center">
            {% if session.get('logged_in') %}
                <span class="text-light me-3 small">User: 
                    <strong class="text-warning">{{ session.get('user', 'User') }} ({{ session.get('role', 'User') }})</strong>
                </span>
                <a href="{{ url_for('logout') }}" class="btn btn-outline-danger btn-sm">Logout</a>
            {% else %}
                <a href="{{ url_for('login') }}" class="btn btn-outline-light btn-sm me-2">Login</a>
            {% endif %}
        </div>
    </div>
</nav>
"""

LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Campus Hardware Inventory</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    """ + NAVBAR_HTML + """
    <div class="container mt-5">
        <div class="row justify-content-center">
            <div class="col-md-5">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white text-center py-3">
                        <h4 class="mb-0">System Login</h4>
                    </div>
                    <div class="card-body p-4">
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
                        <form action="{{ url_for('login') }}" method="POST">
                            <div class="mb-3">
                                <label class="form-label fw-bold">Username / Name</label>
                                <input type="text" name="username" class="form-control" placeholder="Enter username" required autofocus>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-bold">Select Role</label>
                                <select name="role" class="form-select">
                                    <option value="User">Student / Borrower (Request Only)</option>
                                    <option value="Admin">Admin (Add Items & Approve Only)</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label fw-bold">Password</label>
                                <input type="password" name="password" class="form-control" placeholder="Enter password" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100 py-2 fw-bold">Login to System</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

DASHBOARD_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Campus Hardware Inventory</title>
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

        <!-- STRICT ADMIN ONLY: Add Component Panel -->
        {% if session.get('role') == 'Admin' %}
        <div class="card shadow border-primary mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">➕ Admin Control: Add New Hardware Component</h5>
            </div>
            <div class="card-body">
                <form action="{{ url_for('add_component') }}" method="POST" class="row g-3">
                    <div class="col-md-5">
                        <label class="form-label fw-bold">Component Name</label>
                        <input type="text" name="name" class="form-control" placeholder="e.g. Raspberry Pi 4" required>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-bold">Category</label>
                        <input type="text" name="category" class="form-control" placeholder="e.g. Microcontrollers" required>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label fw-bold">Quantity Stock</label>
                        <input type="number" name="quantity" class="form-control" value="1" min="1" required>
                    </div>
                    <div class="col-12 text-end">
                        <button type="submit" class="btn btn-success fw-bold">Save Component</button>
                    </div>
                </form>
            </div>
        </div>
        {% endif %}

        <div class="row">
            <!-- Hardware Inventory Stock -->
            <div class="col-md-5 mb-4">
                <div class="card shadow mb-4">
                    <div class="card-header bg-dark text-white">
                        <h5 class="mb-0">📦 Hardware Inventory Stock</h5>
                    </div>
                    <div class="card-body p-0">
                        <table class="table table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th>Item</th>
                                    <th>Category</th>
                                    <th>Available</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for item in inventory %}
                                <tr>
                                    <td><strong>{{ item.name }}</strong></td>
                                    <td><span class="badge bg-secondary">{{ item.category }}</span></td>
                                    <td><span class="badge bg-info text-dark">{{ item.quantity }} pcs</span></td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Request Form (Available to Everyone) -->
                <div class="card shadow">
                    <div class="card-header bg-secondary text-white">
                        <h5 class="mb-0">📋 Borrower Request Form</h5>
                    </div>
                    <div class="card-body">
                        <form action="{{ url_for('borrow_item') }}" method="POST">
                            <div class="mb-3">
                                <label class="form-label">Borrower Name</label>
                                <input type="text" name="borrower" class="form-control" value="{{ session.get('user', '') }}" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Select Hardware</label>
                                <select name="item_name" class="form-select" required>
                                    {% for item in inventory %}
                                        <option value="{{ item.name }}">{{ item.name }} (Stock: {{ item.quantity }})</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Quantity</label>
                                <input type="number" name="quantity" class="form-control" value="1" min="1" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100 fw-bold">Submit Borrow Request</button>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Monitoring Logs Table -->
            <div class="col-md-7">
                <div class="card shadow">
                    <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">🔄 Request Status & Logs</h5>
                        {% if session.get('role') == 'Admin' %}
                            <span class="badge bg-warning text-dark">Admin Approval Mode</span>
                        {% else %}
                            <span class="badge bg-info text-dark">User View (Read-Only Status)</span>
                        {% endif %}
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-striped table-hover mb-0 align-middle">
                                <thead class="table-light">
                                    <tr>
                                        <th>Borrower</th>
                                        <th>Item</th>
                                        <th>Qty</th>
                                        <th>Status</th>
                                        <th>Action / Control</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% if records %}
                                        {% for rec in records %}
                                        <tr>
                                            <td><strong>{{ rec.borrower }}</strong></td>
                                            <td>{{ rec.item_name }}</td>
                                            <td>{{ rec.quantity }}</td>
                                            <td>
                                                {% if rec.status == 'Pending Approval' %}
                                                    <span class="badge bg-warning text-dark">Pending</span>
                                                {% elif rec.status == 'Approved / Out' %}
                                                    <span class="badge bg-danger">Approved / Out</span>
                                                {% else %}
                                                    <span class="badge bg-success">Returned</span>
                                                {% endif %}
                                            </td>
                                            <td>
                                                {% if session.get('role') == 'Admin' %}
                                                    <!-- ADMIN ONLY CONTROLS -->
                                                    {% if rec.status == 'Pending Approval' %}
                                                        <form action="{{ url_for('approve_item', record_id=rec.id) }}" method="POST">
                                                            <button type="submit" class="btn btn-sm btn-primary fw-bold">Approve Request</button>
                                                        </form>
                                                    {% elif rec.status == 'Approved / Out' %}
                                                        <form action="{{ url_for('return_item', record_id=rec.id) }}" method="POST">
                                                            <button type="submit" class="btn btn-sm btn-success fw-bold">Mark Returned</button>
                                                        </form>
                                                    {% else %}
                                                        <span class="badge bg-secondary">Completed</span>
                                                    {% endif %}
                                                {% else %}
                                                    <!-- USER / BORROWER READ-ONLY STATUS -->
                                                    {% if rec.status == 'Pending Approval' %}
                                                        <span class="badge bg-secondary">Awaiting Admin Approval</span>
                                                    {% elif rec.status == 'Approved / Out' %}
                                                        <span class="badge bg-info text-dark">Item Borrowed (In Use)</span>
                                                    {% else %}
                                                        <span class="badge bg-outline-success text-success">Item Returned</span>
                                                    {% endif %}
                                                {% endif %}
                                            </td>
                                        </tr>
                                        {% endfor %}
                                    {% else %}
                                        <tr>
                                            <td colspan="5" class="text-center text-muted py-4">No borrowing transactions yet.</td>
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

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        role = request.form.get('role', 'User')
        
        session['logged_in'] = True
        session['user'] = username if username else 'User'
        session['role'] = role
        session['login_timestamp'] = get_current_timestamp()
        
        flash(f'Logged in successfully as {role}!', 'success')
        return redirect(url_for('dashboard'))

    return render_template_string(LOGIN_PAGE_HTML)

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    return render_template_string(DASHBOARD_PAGE_HTML, records=BORROW_RECORDS, inventory=HARDWARE_INVENTORY)

@app.route('/add_component', methods=['POST'])
def add_component():
    # BACKEND ROLE CHECK: Bawal mag-add ang hindi Admin
    if not session.get('logged_in') or session.get('role') != 'Admin':
        flash('Permission Denied: Only Admin can add hardware components.', 'danger')
        return redirect(url_for('dashboard'))

    name = request.form.get('name')
    category = request.form.get('category')
    quantity = int(request.form.get('quantity', 1))

    new_item = {
        'id': len(HARDWARE_INVENTORY) + 1,
        'name': name,
        'category': category,
        'quantity': quantity
    }
    HARDWARE_INVENTORY.append(new_item)

    flash(f"Component '{name}' added successfully to inventory!", 'success')
    return redirect(url_for('dashboard'))

@app.route('/borrow', methods=['POST'])
def borrow_item():
    if not session.get('logged_in'):
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    borrower = request.form.get('borrower')
    item_name = request.form.get('item_name')
    quantity = request.form.get('quantity', 1)
    req_time = get_current_timestamp()

    record = {
        'id': len(BORROW_RECORDS) + 1,
        'borrower': borrower if borrower else session.get('user', 'User'),
        'item_name': item_name,
        'quantity': quantity,
        'request_timestamp': req_time,
        'approved_timestamp': None,
        'return_timestamp': None,
        'status': 'Pending Approval'
    }
    BORROW_RECORDS.append(record)

    flash(f"Borrow request for '{item_name}' submitted! Waiting for Admin Approval.", 'info')
    return redirect(url_for('dashboard'))

@app.route('/approve/<int:record_id>', methods=['POST'])
def approve_item(record_id):
    # BACKEND ROLE CHECK: Bawal mag-approve ang Borrower/User
    if not session.get('logged_in') or session.get('role') != 'Admin':
        flash('Permission Denied: Only Admin can approve borrow requests.', 'danger')
        return redirect(url_for('dashboard'))

    approved_time = get_current_timestamp()
    for rec in BORROW_RECORDS:
        if rec['id'] == record_id:
            rec['approved_timestamp'] = approved_time
            rec['status'] = 'Approved / Out'
            flash(f"Request #{record_id} ('{rec['item_name']}') APPROVED!", 'success')
            break

    return redirect(url_for('dashboard'))

@app.route('/return/<int:record_id>', methods=['POST'])
def return_item(record_id):
    # BACKEND ROLE CHECK: Admin lang ang puwedeng mag-mark bilang Returned
    if not session.get('logged_in') or session.get('role') != 'Admin':
        flash('Permission Denied: Only Admin can confirm returned items.', 'danger')
        return redirect(url_for('dashboard'))

    return_time = get_current_timestamp()
    for rec in BORROW_RECORDS:
        if rec['id'] == record_id:
            rec['return_timestamp'] = return_time
            rec['status'] = 'Returned'
            flash(f"Item '{rec['item_name']}' confirmed as returned!", 'success')
            break

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)