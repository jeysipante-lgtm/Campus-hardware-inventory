import os
import smtplib
import random
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from LaboratorySystem_Web_Lab1 import (
    db,
    init_db,
    logger,
    AuthController,
    InventoryController,
    AdminController
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ==========================================
# DATABASE CONFIGURATION
# ==========================================
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres.iclqeezqkjdmmhonnyhw:Jc%4022113312@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    init_db()


# ==========================================
# BREVO SMTP CONFIGURATION & HELPER
# ==========================================
SMTP_SERVER = "smtp-relay.brevo.com"
SMTP_PORT = 2525

# TODO: Palitan ito ng iyong totoong Brevo SMTP Login at Master Password!
SMTP_LOGIN = "your-brevo-email@example.com"
SMTP_PASSWORD = "your-brevo-master-password"

def send_otp_email(receiver_email, otp, intent):
    """Sends a 6-digit OTP using Brevo SMTP."""
    msg = MIMEText(f"Your {intent} One-Time Password (OTP) is: {otp}\n\nPlease enter this code to proceed. Do not share this code with anyone.")
    msg['Subject'] = f"Laboratory System - {intent} OTP"
    msg['From'] = SMTP_LOGIN  # Gamitin ang iyong verified Brevo email
    msg['To'] = receiver_email
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_LOGIN, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Email Error: {e}")
        return False


# ==========================================
# HELPER DECORATORS
# ==========================================

def login_required(f):
    def wrapped(*args, **kwargs):
        if 'username' not in session:
            flash("Please log in first to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapped.__name__ = f.__name__
    return wrapped


def admin_required(f):
    def wrapped(*args, **kwargs):
        if 'username' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        if session.get('role') != 'ADMIN':
            flash("Unauthorized access! Admin rights required.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    wrapped.__name__ = f.__name__
    return wrapped


# ==========================================
# AUTH & OTP ROUTES
# ==========================================

@app.route("/")
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")

        ok, msg, user_data = AuthController.login(username, password)

        if ok:
            session['username'] = user_data['username']
            session['role'] = user_data['role']
            session['student_number'] = user_data.get('student_number', '')
            flash(msg, "success")
            return redirect(url_for('dashboard'))
        else:
            flash(msg, "danger")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("login.html", active_tab="register")
        
    username = request.form.get("username", "").strip()
    student_number = request.form.get("student_number", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    role = request.form.get("role", "USER").strip().upper()

    if not username or not email or not password:
        flash("All registration fields are required.", "danger")
        return redirect(url_for("register"))

    # Generate OTP and save pending data to session
    otp = str(random.randint(100000, 999999))
    session['pending_user'] = {
        'username': username,
        'student_number': student_number,
        'email': email,
        'password': password,
        'role': role,
        'otp': otp
    }

    if send_otp_email(email, otp, intent="Account Registration"):
        flash("We sent a 6-digit code to your email. Please verify.", "info")
        return redirect(url_for("verify_otp", action="register"))
    else:
        flash("Failed to send OTP email. Please check your email/SMTP setup.", "danger")
        return redirect(url_for("register"))


@app.route("/reset_password", methods=["GET", "POST"])
@app.route("/reset_request", methods=["GET", "POST"])
def reset_password():
    if request.method == "GET":
        return render_template("reset.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not username or not email or not new_password or not confirm_password:
        flash("All reset fields are required.", "danger")
        return redirect(url_for("reset_password"))

    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("reset_password"))

    # Generate OTP and save pending reset to session
    otp = str(random.randint(100000, 999999))
    session['pending_reset'] = {
        'username': username,
        'email': email,
        'new_password': new_password,
        'confirm_password': confirm_password,
        'otp': otp
    }

    if send_otp_email(email, otp, intent="Password Reset"):
        flash("We sent a 6-digit code to your email. Please verify.", "info")
        return redirect(url_for("verify_otp", action="reset"))
    else:
        flash("Failed to send OTP email. Please try again.", "danger")
        return redirect(url_for("reset_password"))


@app.route("/verify-otp/<action>", methods=["GET", "POST"])
def verify_otp(action):
    session_key = 'pending_user' if action == "register" else 'pending_reset'

    if session_key not in session:
        flash("Session expired. Please try again.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        user_otp = request.form.get("otp_code", "").strip()
        data = session[session_key]

        if user_otp == data['otp']:
            if action == "register":
                ok, msg = AuthController.register(
                    username=data['username'],
                    email=data['email'],
                    password=data['password'],
                    student_number=data.get('student_number', ''),
                    role=data['role']
                )
                session.pop(session_key, None)
                flash("Account successfully verified and created!", "success" if ok else "warning")
                return redirect(url_for("login"))

            elif action == "reset":
                ok, msg = AuthController.request_password_reset(
                    data['username'],
                    data['email'],
                    data['new_password'],
                    data['confirm_password']
                )
                session.pop(session_key, None)
                flash("Email verified! Password updated successfully.", "success" if ok else "danger")
                return redirect(url_for("login"))
        else:
            flash("Invalid OTP code. Try again.", "danger")

    return render_template("otp_verify.html", action_url=url_for('verify_otp', action=action))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))


# ==========================================
# DASHBOARD & INVENTORY ROUTES
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "ALL")

    items = InventoryController.fetch_all(search_name=search, category=category)
    categories = InventoryController.get_categories()
    total_stocks = InventoryController.get_total_stocks()

    borrows = []
    pending_resets = []
    pending_borrows = []
    pending_returns = []

    if session.get("role") == "ADMIN":
        borrows = InventoryController.fetch_borrows()
        pending_resets = AdminController.fetch_pending_resets()
        pending_borrows = AdminController.fetch_pending_borrows()
        pending_returns = AdminController.fetch_pending_returns()
    else:
        borrows = InventoryController.fetch_borrows(username=session["username"])

    return render_template(
        "dashboard.html",
        items=items,
        categories=categories,
        total_stocks=total_stocks,
        borrows=borrows,
        pending_resets=pending_resets,
        pending_borrows=pending_borrows,
        pending_returns=pending_returns,
        search=search,
        selected_category=category
    )


@app.route("/add_item", methods=["POST"])
@admin_required
def add_item():
    name = request.form.get("item_name", "").strip()
    category = request.form.get("category", "").strip()
    quantity = request.form.get("quantity", "0")
    price = request.form.get("unit_price", "0.0")

    ok, msg = InventoryController.add_item(name, category, quantity, price)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/delete_items", methods=["POST"])
@admin_required
def delete_items():
    item_ids = request.form.getlist("selected_items")
    ok, msg = InventoryController.delete_items(item_ids)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/borrow_item", methods=["POST"])
@login_required
def borrow_item():
    student_number = request.form.get("student_number", "").strip()
    item_id = request.form.get("item_id")
    quantity = int(request.form.get("quantity", 1))

    session['student_number'] = student_number

    ok, msg = InventoryController.request_borrow(
        session["username"], student_number, item_id, quantity
    )
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/return_item/<int:log_id>", methods=["POST"])
@login_required
def return_item(log_id):
    ok, msg = InventoryController.request_return(session["username"], log_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/approve_borrow/<int:log_id>")
@admin_required
def approve_borrow(log_id):
    ok, msg = AdminController.approve_borrow(log_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/reject_borrow/<int:log_id>")
@admin_required
def reject_borrow(log_id):
    ok, msg = AdminController.reject_borrow(log_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/approve_return/<int:log_id>")
@admin_required
def approve_return(log_id):
    ok, msg = AdminController.approve_return(log_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/reject_return/<int:log_id>")
@admin_required
def reject_return(log_id):
    ok, msg = AdminController.reject_return(log_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/export_csv")
@admin_required
def export_csv():
    csv_data = InventoryController.export_to_csv()
    if csv_data:
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=inventory_report.csv"}
        )
    flash("Failed to export CSV.", "danger")
    return redirect(url_for('dashboard'))


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000, use_reloader=False)