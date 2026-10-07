import os
import random
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session, render_template_string

app = Flask(__name__)

# Security Configs
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-fallback-secret-key-12345')

# Mail Configurations (Resend API)
RESEND_API_KEY = os.getenv('RESEND_API_KEY')

# --- In-Memory Database for Components and Borrow Requests ---
COMPONENTS = [
    {"id": 1, "name": "Arduino Uno", "category": "Microcontroller", "quantity": 10},
    {"id": 2, "name": "Breadboard", "category": "Accessories", "quantity": 25},
    {"id": 3, "name": "Digital Multimeter", "category": "Tools", "quantity": 5},
    {"id": 4, "name": "ESP32 Wi-Fi Module", "category": "Microcontroller", "quantity": 15}
]

BORROW_REQUESTS = [
    # Halimbawa: {"id": 1, "username": "student1", "component_id": 1, "component_name": "Arduino Uno", "quantity": 2, "status": "Pending"}
]

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
                                <label class="form-label">Username</label>
                                <input type="text" name="username" class="form-control" required autofocus>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Password</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Role</label>
                                <select name="role" class="form-select">
                                    <option value="Student">Student</option>
                                    <option value="Admin">Admin</option>
                                </select>
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
            <div>
                <span class="text-white me-3">User: {{ session.get('logged_user', 'User') }} ({{ session.get('role', 'Student') }})</span>
                <a href="{{ url_for('login') }}" class="btn btn-outline-light btn-sm">Logout</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <div class="row">
            <!-- Admin Controls -->
            {% if session.get('role') == 'Admin' %}
            <div class="col-md-4 mb-4">
                <div class="card shadow">
                    <div class="card-header bg-dark text-white"><h5>Admin: Add Component</h5></div>
                    <div class="card-body">
                        <form action="{{ url_for('add_component') }}" method="POST">
                            <div class="mb-2">
                                <label class="form-label">Component Name</label>
                                <input type="text" name="name" class="form-control" required>
                            </div>
                            <div class="mb-2">
                                <label class="form-label">Category</label>
                                <input type="text" name="category" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Quantity</label>
                                <input type="number" name="quantity" class="form-control" min="1" required>
                            </div>
                            <button type="submit" class="btn btn-success w-100">Add to Inventory</button>
                        </form>
                        <hr>
                        <a href="{{ url_for('admin_requests') }}" class="btn btn-warning w-100">Review Borrow Requests</a>
                    </div>
                </div>
            </div>
            {% endif %}

            <!-- Inventory / Borrow Section -->
            <div class="{% if session.get('role') == 'Admin' %}col-md-8{% else %}col-md-12{% endif %}">
                <div class="card shadow">
                    <div class="card-header bg-primary text-white"><h5>Available Hardware Components</h5></div>
                    <div class="card-body">
                        <table class="table table-bordered table-striped">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Name</th>
                                    <th>Category</th>
                                    <th>Available Qty</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for comp in components %}
                                <tr>
                                    <td>{{ comp.id }}</td>
                                    <td>{{ comp.name }}</td>
                                    <td>{{ comp.category }}</td>
                                    <td>{{ comp.quantity }}</td>
                                    <td>
                                        {% if comp.quantity > 0 %}
                                        <form action="{{ url_for('borrow_component', comp_id=comp.id) }}" method="POST" class="d-inline-flex">
                                            <input type="number" name="qty" value="1" min="1" max="{{ comp.quantity }}" class="form-control form-control-sm me-1" style="width: 70px;" required>
                                            <button type="submit" class="btn btn-primary btn-sm">Borrow</button>
                                        </form>
                                        {% else %}
                                        <span class="text-danger">Out of Stock</span>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- My Requests & Returns Section -->
                <div class="card shadow mt-4">
                    <div class="card-header bg-secondary text-white"><h5>My Borrowed Items & Requests</h5></div>
                    <div class="card-body">
                        <table class="table table-sm table-bordered">
                            <thead>
                                <tr>
                                    <th>Item</th>
                                    <th>Quantity</th>
                                    <th>Status</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for req in my_requests %}
                                <tr>
                                    <td>{{ req.component_name }}</td>
                                    <td>{{ req.quantity }}</td>
                                    <td>
                                        {% if req.status == 'Pending' %}
                                            <span class="badge bg-warning text-dark">Pending Approval</span>
                                        {% elif req.status == 'Approved' %}
                                            <span class="badge bg-success">Approved / Borrowed</span>
                                        {% elif req.status == 'Returned' %}
                                            <span class="badge bg-secondary">Returned</span>
                                        {% else %}
                                            <span class="badge bg-danger">Rejected</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        {% if req.status == 'Approved' %}
                                        <form action="{{ url_for('return_component', req_id=req.id) }}" method="POST">
                                            <button type="submit" class="btn btn-sm btn-outline-dark">Return Item</button>
                                        </form>
                                        {% else %}
                                            -
                                        {% endif %}
                                    </td>
                                </tr>
                                {% else %}
                                <tr>
                                    <td colspan="4" class="text-center text-muted">No requests found.</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>
        </div>
    </div>
</body>
</html>
"""

ADMIN_REQUESTS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Manage Requests - Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container mt-5">
        <div class="card shadow">
            <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                <h4>Admin Panel - User Borrow Requests</h4>
                <a href="{{ url_for('dashboard') }}" class="btn btn-outline-light btn-sm">Back to Dashboard</a>
            </div>
            <div class="card-body">
                <table class="table table-striped table-bordered">
                    <thead>
                        <tr>
                            <th>Request ID</th>
                            <th>User</th>
                            <th>Component</th>
                            <th>Quantity</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for req in all_requests %}
                        <tr>
                            <td>{{ req.id }}</td>
                            <td>{{ req.username }}</td>
                            <td>{{ req.component_name }}</td>
                            <td>{{ req.quantity }}</td>
                            <td>
                                {% if req.status == 'Pending' %}
                                    <span class="badge bg-warning text-dark">Pending</span>
                                {% else %}
                                    <span class="badge bg-success">{{ req.status }}</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if req.status == 'Pending' %}
                                <a href="{{ url_for('approve_request', req_id=req.id) }}" class="btn btn-success btn-sm">Approve</a>
                                <a href="{{ url_for('reject_request', req_id=req.id) }}" class="btn btn-danger btn-sm">Reject</a>
                                {% else %}
                                    Already {{ req.status }}
                                {% endif %}
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" class="text-center text-muted">No pending borrow requests.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
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
        username = request.form.get('username')
        role = request.form.get('role', 'Student')
        session['logged_user'] = username
        session['role'] = role
        flash('Logged in successfully!', 'success')
        return redirect(url_for('dashboard'))

    try:
        return render_template('login.html')
    except Exception:
        return render_template_string(LOGIN_PAGE_HTML)

@app.route('/dashboard')
def dashboard():
    username = session.get('logged_user', 'Guest')
    my_requests = [r for r in BORROW_REQUESTS if r['username'] == username]
    try:
        return render_template('dashboard.html', components=COMPONENTS, my_requests=my_requests)
    except Exception:
        return render_template_string(DASHBOARD_PAGE_HTML, components=COMPONENTS, my_requests=my_requests)

# --- NEW FEATURES: Add Component, Borrow, Return, Admin Approve ---

@app.route('/component/add', methods=['POST'])
def add_component():
    if session.get('role') != 'Admin':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))
    
    name = request.form.get('name')
    category = request.form.get('category')
    quantity = int(request.form.get('quantity', 1))

    new_id = len(COMPONENTS) + 1
    COMPONENTS.append({"id": new_id, "name": name, "category": category, "quantity": quantity})
    flash('Component added successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/borrow/<int:comp_id>', methods=['POST'])
def borrow_component(comp_id):
    username = session.get('logged_user', 'Guest')
    qty = int(request.form.get('qty', 1))

    component = next((c for c in COMPONENTS if c['id'] == comp_id), None)
    if component and component['quantity'] >= qty:
        # Bawas muna ang stock o hintayin ang approval? Ibabawas natin kapag na-approve na ng admin, o i-pending muna.
        req_id = len(BORROW_REQUESTS) + 1
        BORROW_REQUESTS.append({
            "id": req_id,
            "username": username,
            "component_id": comp_id,
            "component_name": component['name'],
            "quantity": qty,
            "status": "Pending"
        })
        flash('Borrow request submitted! Waiting for Admin approval.', 'info')
    else:
        flash('Requested quantity exceeds available stock.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/return/<int:req_id>', methods=['POST'])
def return_component(req_id):
    req = next((r for r in BORROW_REQUESTS if r['id'] == req_id), None)
    if req and req['status'] == 'Approved':
        req['status'] = 'Returned'
        # Ibalik ang quantity sa components
        component = next((c for c in COMPONENTS if c['id'] == req['component_id']), None)
        if component:
            component['quantity'] += req['quantity']
        flash('Item successfully returned to inventory.', 'success')
    else:
        flash('Invalid action.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/admin/requests')
def admin_requests():
    if session.get('role') != 'Admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    try:
        return render_template('admin_requests.html', all_requests=BORROW_REQUESTS)
    except Exception:
        return render_template_string(ADMIN_REQUESTS_HTML, all_requests=BORROW_REQUESTS)

@app.route('/admin/approve/<int:req_id>')
def approve_request(req_id):
    if session.get('role') != 'Admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    req = next((r for r in BORROW_REQUESTS if r['id'] == req_id), None)
    if req and req['status'] == 'Pending':
        component = next((c for c in COMPONENTS if c['id'] == req['component_id']), None)
        if component and component['quantity'] >= req['quantity']:
            component['quantity'] -= req['quantity']
            req['status'] = 'Approved'
            flash(f"Request #{req_id} approved successfully!", 'success')
        else:
            flash("Not enough stock to approve this request.", 'danger')
    return redirect(url_for('admin_requests'))

@app.route('/admin/reject/<int:req_id>')
def reject_request(req_id):
    if session.get('role') != 'Admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    req = next((r for r in BORROW_REQUESTS if r['id'] == req_id), None)
    if req and req['status'] == 'Pending':
        req['status'] = 'Rejected'
        flash(f"Request #{req_id} rejected.", 'warning')
    return redirect(url_for('admin_requests'))

if __name__ == '__main__':
    app.run(debug=True)