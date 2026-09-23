import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from LaboratorySystem_Web_Lab1 import (
    init_db,
    logger,
    AuthController,
    InventoryController,
    AdminController
)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Kailangan para sa session at flash messages

# I-initialize ang database bago patakbuhin ang server
init_db()


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
# ROUTES
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
            is_locked = (msg == "ACCOUNT_LOCKED")
            if is_locked:
                flash("Your account has been locked due to too many failed attempts.", "danger")
                return render_template("login.html", locked=True, locked_username=username)

            flash(msg, "danger")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        student_number = request.form.get("student_number", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "USER").strip()  # Kukunin ang piniling role (USER or ADMIN)

        # Ipasa ang student_number at role sa AuthController.register
        ok, msg = AuthController.register(
            username=username,
            email=email,
            password=password,
            student_number=student_number,
            role=role
        )

        if ok:
            flash(msg, "success")
            return redirect(url_for('login'))
        else:
            flash(msg, "danger")
            return render_template("login.html", active_tab="register")

    return render_template("login.html", active_tab="register")


@app.route("/reset_password", methods=["GET", "POST"])
@app.route("/reset_request", methods=["GET", "POST"])  # Alias para maiwasan ang BuildError mula sa template
def reset_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        ok, msg = AuthController.request_password_reset(
            username, email, new_password, confirm_password
        )

        if ok:
            flash(msg, "info")
            return redirect(url_for('login'))
        else:
            flash(msg, "danger")

    return render_template("reset.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))


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


@app.route("/admin/approve_borrow/<int:log_id>")
@admin_required
def approve_borrow(log_id):
    ok, msg = AdminController.approve_borrow(log_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/admin/reject_borrow/<int:log_id>")
@admin_required
def reject_borrow(log_id):
    ok, msg = AdminController.reject_borrow(log_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/admin/approve_return/<int:log_id>")
@admin_required
def approve_return(log_id):
    ok, msg = AdminController.approve_return(log_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/admin/reject_return/<int:log_id>")
@admin_required
def reject_return(log_id):
    ok, msg = AdminController.reject_return(log_id)
    flash(msg, "success" if ok else "danger")
    return redirect(url_for('dashboard'))


@app.route("/admin/process_resets", methods=["POST"])
@admin_required
def process_resets():
    request_ids = request.form.getlist("selected_resets")
    action = request.form.get("action")

    if action == "approve":
        ok, msg = AdminController.approve_resets(request_ids)
    elif action == "reject":
        ok, msg = AdminController.reject_resets(request_ids)
    else:
        ok, msg = False, "Invalid action."

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
    print("\n" + "="*50)
    print(" Application is starting...")
    print(" Open your browser and go to: http://127.0.0.1:5000")
    print("="*50 + "\n", flush=True)

    app.run(debug=True, host="127.0.0.1", port=5000, use_reloader=False)